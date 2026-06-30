from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import desc

from models.database import db
from models.transaction import AuditLog
from middleware.auth import role_required

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")


@audit_bp.route("/", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def list_logs():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    action = request.args.get("action")
    severity = request.args.get("severity")
    user_id = request.args.get("user_id")

    q = AuditLog.query
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if severity:
        q = q.filter_by(severity=severity)
    if user_id:
        q = q.filter_by(user_id=user_id)

    pagination = q.order_by(desc(AuditLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        "logs": [l.to_dict() for l in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "page": page,
    }), 200
