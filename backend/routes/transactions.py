import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import desc, or_

from models.database import db
from models.user import User
from models.transaction import Transaction, AuditLog
from services.fraud_service import (
    calculate_risk_score, generate_explanation, get_shap_values,
    COUNTRY_NAMES, COUNTRY_COORDS
)
from services.auth_service import log_action
from middleware.rate_limit import rate_limit

txn_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")

# Fraud check functions (compatible with new DB model)
def _check_amount(user_id, amount):
    from flask import current_app
    mult = current_app.config.get("AMOUNT_MULTIPLIER", 1.5)
    prev = Transaction.query.filter_by(user_id=user_id, status="approved").all()
    if not prev:
        return True, None, 0
    max_past = max(t.amount for t in prev)
    limit = max_past * mult
    return amount <= limit, limit, max_past

def _check_location(country):
    from flask import current_app
    allowed = current_app.config.get("ALLOWED_COUNTRIES", [])
    return country in allowed

def _check_frequency(user_id):
    from flask import current_app
    from datetime import timedelta
    win = current_app.config.get("FREQ_WINDOW_MIN", 10)
    limit = current_app.config.get("MAX_TXN_IN_WINDOW", 3)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=win)
    count = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.created_at > cutoff
    ).count()
    return count < limit, count

def _check_duplicate(user_id, amount, merchant):
    from flask import current_app
    from datetime import timedelta
    win = current_app.config.get("DUP_WINDOW_MIN", 5)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=win)
    count = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.amount == amount,
        Transaction.merchant == merchant,
        Transaction.created_at > cutoff,
    ).count()
    return count == 0, count


@txn_bp.route("/analyze", methods=["POST"])
@jwt_required()
@rate_limit(max_calls=30, window=60)
def analyze():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    data = request.json or {}

    amount = float(data.get("amount", 0))
    country = data.get("country", "MA").upper()
    merchant = data.get("merchant", "")
    currency = data.get("currency", "MAD")
    card_last4 = data.get("card_last4", "")
    user_label = data.get("user_label", user.username if user else "unknown")

    checks = []
    fraud = False

    ok, limit, max_past = _check_amount(user_id, amount)
    checks.append({"check": "Limite de montant", "icon": "💰", "passed": ok,
        "detail": f"Montant: {amount:.2f} {currency} | Max: {max_past:.2f} | Limite: {limit:.2f}" if limit
                  else f"Montant: {amount:.2f} {currency} | Premier achat — autorisé"})
    if not ok: fraud = True

    ok_loc = _check_location(country)
    checks.append({"check": "Vérification de localisation", "icon": "🌍", "passed": ok_loc,
        "detail": f"Pays: {COUNTRY_NAMES.get(country, country)} ({country}) | {'✓ Autorisé' if ok_loc else '✗ Non autorisé'}"})
    if not ok_loc: fraud = True

    ok_freq, cnt = _check_frequency(user_id)
    checks.append({"check": "Fréquence des transactions", "icon": "⚡", "passed": ok_freq,
        "detail": f"{cnt} transaction(s) récente(s) | Limite dépassée" if not ok_freq else f"{cnt} transaction(s) récente(s) — normal"})
    if not ok_freq: fraud = True

    ok_dup, dup_cnt = _check_duplicate(user_id, amount, merchant)
    checks.append({"check": "Détection de doublons", "icon": "🔁", "passed": ok_dup,
        "detail": f"{dup_cnt} doublon(s) détecté(s)" if not ok_dup else "Aucun doublon"})
    if not ok_dup: fraud = True

    # Get user history for risk scoring
    user_history = [t.to_dict() for t in
                    Transaction.query.filter_by(user_id=user_id).order_by(desc(Transaction.created_at)).limit(20).all()]

    risk_score, confidence, risk_level = calculate_risk_score(checks, amount, country, user_history)
    explanation = generate_explanation(checks, risk_score, amount, country, merchant)
    shap_values = get_shap_values(checks, risk_score)

    status = "blocked" if fraud else "approved"
    coords = COUNTRY_COORDS.get(country, (0, 0))

    import uuid
    txn_count = Transaction.query.count()
    txn = Transaction(
        id=str(uuid.uuid4()),
        txn_ref=f"TXN{str(txn_count + 1).zfill(6)}",
        user_id=user_id,
        user_label=user_label,
        amount=amount, currency=currency,
        country=country, merchant=merchant,
        card_last4=card_last4,
        ip_address=request.remote_addr,
        status=status,
        risk_score=risk_score,
        confidence=confidence,
        risk_level=risk_level,
        checks_json=json.dumps(checks),
        explanation=explanation,
        latitude=coords[0], longitude=coords[1],
    )
    db.session.add(txn)
    db.session.commit()

    log_action(user_id, "transaction_analyzed", "transaction", txn.id,
               details=f"Amount: {amount} {currency}, Status: {status}, Risk: {risk_score}",
               severity="warning" if fraud else "info")

    # Emit real-time event
    try:
        from models.database import socketio
        socketio.emit("new_transaction", txn.to_dict(), namespace="/")
    except Exception:
        pass

    return jsonify({
        "fraud": fraud,
        "status": status,
        "transaction": txn.to_dict(),
        "checks": checks,
        "risk_score": risk_score,
        "confidence": confidence,
        "risk_level": risk_level,
        "explanation": explanation,
        "shap_values": shap_values,
    }), 200


@txn_bp.route("/", methods=["GET"])
@jwt_required()
def list_transactions():
    claims = get_jwt()
    user_id = get_jwt_identity()
    role = claims.get("role", "user")

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 25)), 100)
    status = request.args.get("status")
    risk_level = request.args.get("risk_level")
    country = request.args.get("country")
    search = request.args.get("search", "")
    sort = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")

    q = Transaction.query
    if role not in ("admin", "manager", "analyst"):
        q = q.filter_by(user_id=user_id)
    if status:
        q = q.filter_by(status=status)
    if risk_level:
        q = q.filter_by(risk_level=risk_level)
    if country:
        q = q.filter_by(country=country)
    if search:
        q = q.filter(or_(
            Transaction.txn_ref.ilike(f"%{search}%"),
            Transaction.merchant.ilike(f"%{search}%"),
            Transaction.user_label.ilike(f"%{search}%"),
        ))

    sort_col = getattr(Transaction, sort, Transaction.created_at)
    if order == "desc":
        q = q.order_by(desc(sort_col))
    else:
        q = q.order_by(sort_col)

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "transactions": [t.to_dict() for t in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "page": page,
        "per_page": per_page,
    }), 200


@txn_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    claims = get_jwt()
    user_id = get_jwt_identity()
    role = claims.get("role", "user")

    q = Transaction.query
    if role not in ("admin", "manager", "analyst"):
        q = q.filter_by(user_id=user_id)

    all_txns = q.all()
    approved = [t for t in all_txns if t.status == "approved"]
    blocked = [t for t in all_txns if t.status == "blocked"]
    total_amount = sum(t.amount for t in approved)
    avg_risk = sum(t.risk_score for t in all_txns) / len(all_txns) if all_txns else 0

    # By country
    by_country = {}
    for t in all_txns:
        by_country[t.country] = by_country.get(t.country, 0) + 1

    # By day (last 30 days)
    from datetime import timedelta
    from collections import defaultdict
    daily = defaultdict(lambda: {"approved": 0, "blocked": 0, "amount": 0})
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    for t in all_txns:
        if t.created_at and t.created_at > cutoff:
            day = t.created_at.strftime("%Y-%m-%d")
            daily[day][t.status] += 1
            if t.status == "approved":
                daily[day]["amount"] += t.amount

    # Risk distribution
    risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for t in all_txns:
        risk_dist[t.risk_level] = risk_dist.get(t.risk_level, 0) + 1

    return jsonify({
        "total": len(all_txns),
        "approved": len(approved),
        "blocked": len(blocked),
        "total_amount": round(total_amount, 2),
        "fraud_rate": round(len(blocked) / len(all_txns) * 100, 1) if all_txns else 0,
        "avg_risk_score": round(avg_risk, 1),
        "by_country": by_country,
        "daily": [{"date": k, **v} for k, v in sorted(daily.items())],
        "risk_distribution": risk_dist,
    }), 200


@txn_bp.route("/map", methods=["GET"])
@jwt_required()
def map_data():
    txns = Transaction.query.filter(
        Transaction.latitude.isnot(None),
        Transaction.longitude.isnot(None),
    ).order_by(desc(Transaction.created_at)).limit(500).all()

    return jsonify([{
        "id": t.id,
        "lat": t.latitude,
        "lon": t.longitude,
        "country": t.country,
        "amount": t.amount,
        "status": t.status,
        "risk_level": t.risk_level,
        "merchant": t.merchant,
    } for t in txns]), 200


@txn_bp.route("/export", methods=["GET"])
@jwt_required()
def export_csv():
    from flask import Response
    claims = get_jwt()
    user_id = get_jwt_identity()
    role = claims.get("role", "user")

    q = Transaction.query
    if role not in ("admin", "manager", "analyst"):
        q = q.filter_by(user_id=user_id)

    txns = q.order_by(desc(Transaction.created_at)).limit(5000).all()

    lines = ["Reference,Date,Utilisateur,Marchand,Montant,Devise,Pays,Score,Niveau,Statut"]
    for t in txns:
        date = t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else ""
        lines.append(f"{t.txn_ref},{date},{t.user_label or ''},{t.merchant},{t.amount:.2f},{t.currency},{t.country},{t.risk_score:.1f},{t.risk_level},{t.status}")

    log_action(user_id, "transactions_exported", "transaction", None,
               details=f"Exported {len(txns)} transactions as CSV")

    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=fds-transactions.csv"}
    )
