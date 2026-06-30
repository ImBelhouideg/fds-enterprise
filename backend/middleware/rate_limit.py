from functools import wraps
from flask import jsonify, request
from services.redis_service import get_redis
import time

def rate_limit(max_calls: int = 60, window: int = 60, key_func=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            r = get_redis()
            if not r:
                return fn(*args, **kwargs)
            if key_func:
                key = f"rl:{fn.__name__}:{key_func()}"
            else:
                key = f"rl:{fn.__name__}:{request.remote_addr}"
            pipe = r.pipeline()
            now = time.time()
            window_start = now - window
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = pipe.execute()
            count = results[2]
            if count > max_calls:
                return jsonify({"error": "Rate limit exceeded", "retry_after": window}), 429
            return fn(*args, **kwargs)
        return wrapper
    return decorator
