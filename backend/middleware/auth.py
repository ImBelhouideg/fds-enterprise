from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from models.database import db
from models.user import User

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "user")
            if user_role not in roles:
                return jsonify({"error": "Insufficient permissions", "required": list(roles)}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    from flask_jwt_extended import get_jwt_identity
    user_id = get_jwt_identity()
    if not user_id:
        return None
    return db.session.get(User, user_id)

def active_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user or not user.is_active:
            return jsonify({"error": "Account is disabled"}), 403
        return fn(*args, **kwargs)
    return wrapper
