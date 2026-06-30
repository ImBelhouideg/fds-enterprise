"""FDS Enterprise Platform v3.0 — Flask Application Factory"""
import os, time, logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from config.settings import get_config
from models.database import db, bcrypt, jwt, mail, socketio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("fds")

REQUEST_COUNT   = Counter("fds_requests_total", "HTTP requests", ["method","endpoint","status"])
REQUEST_LATENCY = Histogram("fds_request_seconds", "Latency", ["endpoint"])

def create_app(cfg=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    cfg = cfg or get_config()
    app.config.from_object(cfg)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent",
                      logger=False, engineio_logger=False)

    CORS(app, origins=app.config.get("CORS_ORIGINS","*"), supports_credentials=True,
         allow_headers=["Content-Type","Authorization"],
         methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"])

    @jwt.expired_token_loader
    def _expired(h, p): return jsonify({"error":"Token expiré","code":"TOKEN_EXPIRED"}), 401
    @jwt.invalid_token_loader
    def _invalid(e):    return jsonify({"error":"Token invalide","code":"TOKEN_INVALID"}), 401
    @jwt.unauthorized_loader
    def _missing(e):    return jsonify({"error":"Authentification requise","code":"TOKEN_MISSING"}), 401

    @app.before_request
    def _before(): from flask import g; g.t0 = time.time()

    @app.after_request
    def _after(r):
        from flask import g
        lat = time.time() - getattr(g,"t0",time.time())
        ep  = request.endpoint or "unknown"
        REQUEST_COUNT.labels(request.method, ep, r.status_code).inc()
        REQUEST_LATENCY.labels(ep).observe(lat)
        r.headers.update({
            "X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY",
            "X-XSS-Protection":"1; mode=block","X-FDS-Version":"3.0.0",
        })
        return r

    from routes.auth          import auth_bp
    from routes.transactions  import txn_bp
    from routes.users         import users_bp
    from routes.audit         import audit_bp
    from routes.notifications import notif_bp
    from routes.monitoring    import monitor_bp
    from routes.settings      import settings_bp
    for bp in [auth_bp, txn_bp, users_bp, audit_bp, notif_bp, monitor_bp, settings_bp]:
        app.register_blueprint(bp)

    @app.route("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.route("/health")
    def health():
        from services.redis_service import get_redis
        r = get_redis()
        db_ok = False
        try:
            db.session.execute(db.text("SELECT 1")); db.session.remove(); db_ok = True
        except Exception: pass
        return jsonify({
            "status": "ok" if (db_ok and r) else "degraded",
            "database": "connected" if db_ok else "unavailable",
            "redis": "connected" if r else "unavailable",
            "version": "3.0.0",
        }), 200

    @app.route("/", defaults={"path":""})
    @app.route("/<path:path>")
    def spa(path):
        if path.startswith(("api/","metrics","health","static/")):
            return jsonify({"error":"Not found"}), 404
        return send_from_directory(app.template_folder, "index.html")

    @app.errorhandler(404)
    def e404(e): return jsonify({"error":"Not found"}), 404
    @app.errorhandler(500)
    def e500(e): logger.error(f"500: {e}"); return jsonify({"error":"Internal server error"}), 500

    with app.app_context():
        try:
            db.create_all()
            from models.user import User
            from models.transaction import Transaction, AuditLog, Notification
            from utils.seed import seed_demo_data
            seed_demo_data(db, User, Transaction, AuditLog, bcrypt)
            logger.info("✅ DB initialized")
        except Exception as e:
            logger.warning(f"⚠️  DB init skipped: {e}")

    @socketio.on("connect")
    def _ws_connect(): pass
    @socketio.on("ping")
    def _ws_ping(d): socketio.emit("pong", {"ts": time.time()})

    return app

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000,
                 debug=os.environ.get("FLASK_DEBUG","0")=="1")
