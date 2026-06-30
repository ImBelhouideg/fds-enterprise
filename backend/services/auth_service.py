import uuid, pyotp, logging
from datetime import datetime, timezone, timedelta
from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token

logger = logging.getLogger("fds.auth")

def create_tokens(user):
    claims = {"role": user.role, "email": user.email, "username": user.username}
    access  = create_access_token(identity=user.id, additional_claims=claims)
    refresh = create_refresh_token(identity=user.id)
    return {"access_token": access, "refresh_token": refresh, "user": user.to_dict()}

def generate_token(n=32):
    return uuid.uuid4().hex + uuid.uuid4().hex[:n-32]

def log_action(user_id, action, resource_type=None, resource_id=None,
               details=None, severity="info"):
    try:
        from models.database import db
        from models.transaction import AuditLog
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=(request.headers.get("User-Agent","")[:500] if request else None),
            severity=severity,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.warning(f"Could not log action {action}: {e}")

def setup_2fa(user):
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="FDS Platform")
    return secret, uri

def verify_2fa(user, code):
    if not user.two_factor_secret:
        return False
    totp = pyotp.TOTP(user.two_factor_secret)
    return totp.verify(code, valid_window=1)
