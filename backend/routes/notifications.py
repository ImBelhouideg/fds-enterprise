from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc

from models.database import db
from models.transaction import Notification

notif_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notif_bp.route("/", methods=["GET"])
@jwt_required()
def list_notifications():
    user_id = get_jwt_identity()
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    unread_only = request.args.get("unread") == "true"

    q = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        q = q.filter_by(is_read=False)

    pagination = q.order_by(desc(Notification.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({
        "notifications": [n.to_dict() for n in pagination.items],
        "total": pagination.total,
        "unread_count": unread_count,
        "page": page,
    }), 200


@notif_bp.route("/<notif_id>/read", methods=["POST"])
@jwt_required()
def mark_read(notif_id):
    user_id = get_jwt_identity()
    n = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
    if not n:
        return jsonify({"error": "Not found"}), 404
    n.is_read = True
    db.session.commit()
    return jsonify({"message": "Marked as read"}), 200


@notif_bp.route("/read-all", methods=["POST"])
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200
