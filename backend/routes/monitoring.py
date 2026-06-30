import time
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from middleware.auth import role_required
from services.redis_service import get_redis
from models.database import db
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

monitor_bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")


def _get_sys_stats():
    try:
        import psutil
        cpu  = psutil.cpu_percent(interval=0.1)
        mem  = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net  = psutil.net_io_counters()
        return {
            "cpu":     {"percent": round(cpu,1), "count": psutil.cpu_count()},
            "memory":  {"total": mem.total, "used": mem.used,
                        "percent": round(mem.percent,1), "available": mem.available},
            "disk":    {"total": disk.total, "used": disk.used,
                        "percent": round(disk.percent,1), "free": disk.free},
            "network": {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv},
        }
    except ImportError:
        return {
            "cpu":    {"percent": 0, "count": 1},
            "memory": {"total": 0, "used": 0, "percent": 0, "available": 0},
            "disk":   {"total": 0, "used": 0, "percent": 0, "free": 0},
            "network":{"bytes_sent": 0, "bytes_recv": 0},
        }


@monitor_bp.route("/system", methods=["GET"])
@jwt_required()
@role_required("admin", "manager")
def system_stats():
    stats = _get_sys_stats()

    # Redis info
    r = get_redis()
    redis_info = {"status": "unavailable"}
    if r:
        try:
            info = r.info()
            redis_info = {
                "status":             "connected",
                "used_memory_human":  info.get("used_memory_human", "N/A"),
                "connected_clients":  info.get("connected_clients", 0),
                "keyspace_hits":      info.get("keyspace_hits", 0),
                "keyspace_misses":    info.get("keyspace_misses", 0),
                "uptime_in_seconds":  info.get("uptime_in_seconds", 0),
            }
        except Exception:
            redis_info = {"status": "error"}

    # DB check
    db_status = "healthy"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_status = "error"

    return jsonify({
        **stats,
        "redis":    redis_info,
        "database": {"status": db_status},
        "timestamp": time.time(),
    }), 200


@monitor_bp.route("/health", methods=["GET"])
def health():
    r = get_redis()
    db_ok = True
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_ok = False
    return jsonify({
        "status":   "ok" if db_ok else "degraded",
        "redis":    "connected" if r else "unavailable",
        "database": "connected" if db_ok else "error",
        "timestamp": time.time(),
    }), 200
