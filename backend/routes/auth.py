from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt, create_access_token
)
from datetime import datetime, timezone, timedelta
import re

from models.database import db
from models.user import User
from models.transaction import Notification
from services.auth_service import (
    create_tokens, generate_token, log_action, setup_2fa, verify_2fa
)
from middleware.rate_limit import rate_limit

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


@auth_bp.route("/register", methods=["POST"])
@rate_limit(max_calls=5, window=300)
def register():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()

    if not email or not EMAIL_RE.match(email):
        return jsonify({"error": "Email invalide"}), 400
    if len(username) < 3:
        return jsonify({"error": "Nom d'utilisateur trop court (min 3 caractères)"}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe trop court (min 8 caractères)"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email déjà utilisé"}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Nom d'utilisateur déjà pris"}), 409

    user = User(
        email=email, username=username,
        first_name=first_name, last_name=last_name,
        role="analyst",
        is_active=True, is_verified=True,  # auto-verify for demo
        avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    log_action(user.id, "user_registered", "user", user.id)
    tokens = create_tokens(user)
    return jsonify({"message": "Compte créé avec succès", **tokens}), 201


@auth_bp.route("/login", methods=["POST"])
@rate_limit(max_calls=10, window=60)
def login():
    data = request.json or {}
    identifier = data.get("email", data.get("username", "")).strip().lower()
    password = data.get("password", "")
    remember_me = data.get("remember_me", False)

    try:
        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()
    except Exception as db_err:
        current_app.logger.error(f"DB unavailable during login: {db_err}")
        return jsonify({"error": "Service temporairement indisponible. Réessayez dans quelques instants."}), 503

    if not user or not user.check_password(password):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.session.commit()
        log_action(None, "login_failed", "user", identifier,
                   details=f"Failed login attempt for {identifier}", severity="warning")
        return jsonify({"error": "Identifiants incorrects"}), 401

    if not user.is_active:
        return jsonify({"error": "Compte désactivé. Contactez l'administrateur."}), 403

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        return jsonify({"error": f"Compte temporairement verrouillé jusqu'à {user.locked_until.strftime('%H:%M')}"}), 423

    if user.two_factor_enabled:
        totp_code = data.get("totp_code")
        if not totp_code:
            return jsonify({"requires_2fa": True, "user_id": user.id}), 200
        if not verify_2fa(user, totp_code):
            return jsonify({"error": "Code 2FA invalide"}), 401

    # Successful login
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    user.last_login_ip = request.remote_addr
    user.login_count = (user.login_count or 0) + 1
    db.session.commit()

    log_action(user.id, "user_login", "user", user.id,
               details=f"Login from {request.remote_addr}")

    tokens = create_tokens(user)
    return jsonify(tokens), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({"error": "User not found or disabled"}), 401
    claims = {"role": user.role, "email": user.email, "username": user.username}
    new_token = create_access_token(identity=user_id, additional_claims=claims)
    return jsonify({"access_token": new_token, "token_type": "Bearer"}), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    log_action(user_id, "user_logout", "user", user_id)
    return jsonify({"message": "Déconnecté avec succès"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict(include_sensitive=True)), 200


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json or {}
    for field in ["first_name", "last_name", "avatar_url"]:
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    log_action(user_id, "profile_updated", "user", user_id)
    return jsonify(user.to_dict()), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json or {}
    current_pw = data.get("current_password", "")
    new_pw = data.get("new_password", "")
    if not user.check_password(current_pw):
        return jsonify({"error": "Mot de passe actuel incorrect"}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "Nouveau mot de passe trop court"}), 400
    user.set_password(new_pw)
    db.session.commit()
    log_action(user_id, "password_changed", "user", user_id, severity="warning")
    return jsonify({"message": "Mot de passe modifié avec succès"}), 200


@auth_bp.route("/2fa/setup", methods=["POST"])
@jwt_required()
def setup_2fa_route():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    result = setup_2fa(user)
    return jsonify(result), 200


@auth_bp.route("/2fa/verify", methods=["POST"])
@jwt_required()
def enable_2fa():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    code = (request.json or {}).get("code", "")
    if verify_2fa(user, code):
        user.two_factor_enabled = True
        db.session.commit()
        log_action(user_id, "2fa_enabled", "user", user_id, severity="warning")
        return jsonify({"message": "2FA activé avec succès"}), 200
    return jsonify({"error": "Code invalide"}), 400


@auth_bp.route("/2fa/disable", methods=["POST"])
@jwt_required()
def disable_2fa():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.two_factor_enabled = False
    user.two_factor_secret = None
    db.session.commit()
    log_action(user_id, "2fa_disabled", "user", user_id, severity="warning")
    return jsonify({"message": "2FA désactivé"}), 200
