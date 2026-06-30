from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timezone, timedelta
from sqlalchemy import desc

from models.database import db
from models.user import User
from models.transaction import AuditLog, Notification
from services.auth_service import log_action
from middleware.auth import role_required

users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def list_users():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    search = request.args.get("search", "")
    role = request.args.get("role")

    q = User.query
    if search:
        q = q.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))
        )
    if role:
        q = q.filter_by(role=role)

    pagination = q.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "users": [u.to_dict(include_sensitive=True) for u in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "page": page,
    }), 200


@users_bp.route("/<user_id>", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict(include_sensitive=True)), 200


@users_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("admin")
def create_user():
    data = request.json or {}
    admin_id = get_jwt_identity()
    import uuid, re
    email = data.get("email", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "analyst")

    if not email or not username or not password:
        return jsonify({"error": "Email, username et password requis"}), 400
    if role not in ("admin", "manager", "analyst", "user"):
        return jsonify({"error": "Rôle invalide"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email déjà utilisé"}), 409

    user = User(
        id=str(uuid.uuid4()),
        email=email, username=username,
        role=role, is_active=True, is_verified=True,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    log_action(admin_id, "user_created", "user", user.id,
               details=f"Created user {email} with role {role}")
    return jsonify(user.to_dict()), 201


@users_bp.route("/<user_id>", methods=["PUT"])
@jwt_required()
@role_required("admin")
def update_user(user_id):
    admin_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.json or {}
    for field in ["first_name", "last_name", "role", "is_active", "avatar_url"]:
        if field in data:
            setattr(user, field, data[field])
    if "password" in data and len(data["password"]) >= 8:
        user.set_password(data["password"])
    db.session.commit()
    log_action(admin_id, "user_updated", "user", user_id,
               details=f"Updated fields: {list(data.keys())}")
    return jsonify(user.to_dict()), 200


@users_bp.route("/<user_id>", methods=["DELETE"])
@jwt_required()
@role_required("admin")
def delete_user(user_id):
    admin_id = get_jwt_identity()
    if user_id == admin_id:
        return jsonify({"error": "Cannot delete your own account"}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    email = user.email
    db.session.delete(user)
    db.session.commit()
    log_action(admin_id, "user_deleted", "user", user_id,
               details=f"Deleted user {email}", severity="warning")
    return jsonify({"message": "Utilisateur supprimé"}), 200


@users_bp.route("/<user_id>/toggle-block", methods=["POST"])
@jwt_required()
@role_required("admin", "manager")
def toggle_block(user_id):
    admin_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.is_active = not user.is_active
    db.session.commit()
    action = "user_unblocked" if user.is_active else "user_blocked"
    log_action(admin_id, action, "user", user_id, severity="warning")
    return jsonify({"message": f"Utilisateur {'débloqué' if user.is_active else 'bloqué'}", "is_active": user.is_active}), 200


@users_bp.route("/<user_id>/change-role", methods=["POST"])
@jwt_required()
@role_required("admin")
def change_role(user_id):
    admin_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    new_role = (request.json or {}).get("role")
    if new_role not in ("admin", "manager", "analyst", "user"):
        return jsonify({"error": "Rôle invalide"}), 400
    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_action(admin_id, "role_changed", "user", user_id,
               details=f"Role: {old_role} → {new_role}", severity="warning")
    return jsonify(user.to_dict()), 200
