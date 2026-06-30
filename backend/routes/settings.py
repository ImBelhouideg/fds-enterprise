from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.database import db
from models.user import User
from services.auth_service import log_action
import json

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")

def _get_prefs(user_id):
    from services.redis_service import get_redis
    r = get_redis()
    if r:
        try:
            raw = r.get(f"settings:{user_id}")
            if raw: return json.loads(raw)
        except Exception: pass
    return {}

def _set_prefs(user_id, prefs):
    from services.redis_service import get_redis
    r = get_redis()
    if r:
        try: r.setex(f"settings:{user_id}", 86400*30, json.dumps(prefs))
        except Exception: pass

@settings_bp.route("/", methods=["GET"])
@jwt_required()
def get_settings():
    uid = get_jwt_identity()
    prefs = _get_prefs(uid)
    return jsonify({
        "theme":                  prefs.get("theme", "dark"),
        "language":               prefs.get("language", "fr"),
        "timezone":               prefs.get("timezone", "Africa/Casablanca"),
        "notifications_email":    prefs.get("notifications_email", True),
        "notifications_push":     prefs.get("notifications_push", True),
        "notifications_sound":    prefs.get("notifications_sound", True),
        "fraud_alert_threshold":  prefs.get("fraud_alert_threshold", 50),
        "sidebar_collapsed":      prefs.get("sidebar_collapsed", False),
    }), 200

@settings_bp.route("/", methods=["PUT"])
@jwt_required()
def update_settings():
    uid = get_jwt_identity()
    data = request.json or {}
    prefs = _get_prefs(uid)
    prefs.update(data)
    _set_prefs(uid, prefs)
    log_action(uid, "settings_updated", "settings", uid)
    return jsonify({"message": "Settings saved", "settings": prefs}), 200
