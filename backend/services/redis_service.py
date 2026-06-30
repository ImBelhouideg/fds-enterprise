import os, logging
logger = logging.getLogger("fds.redis")

_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        host = os.environ.get("REDIS_HOST", "redis")
        port = int(os.environ.get("REDIS_PORT", 6379))
        pwd  = os.environ.get("REDIS_PASSWORD", "") or None
        db   = int(os.environ.get("REDIS_DB", 0))
        r = redis.Redis(host=host, port=port, password=pwd, db=db,
                        decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        _redis_client = r
        logger.info(f"Redis connected: {host}:{port}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None
