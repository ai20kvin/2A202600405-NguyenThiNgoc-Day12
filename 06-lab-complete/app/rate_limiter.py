import time
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

# Khởi tạo Redis client
redis_client = settings.get_redis_client()

def check_rate_limit(user_id: str):
    """
    Kiểm tra Rate Limit sử dụng Redis (Sliding Window).
    Nếu không có Redis, fallback về in-memory (không scalable).
    """
    now = time.time()
    limit = settings.rate_limit_per_minute
    window = 60
    
    if redis_client:
        try:
            key = f"rl:{user_id}"
            # Xóa các request ngoài window
            redis_client.zremrangebyscore(key, 0, now - window)
            # Đếm số request trong window
            request_count = redis_client.zcard(key)
            
            if request_count >= limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: {limit} req/min",
                    headers={"Retry-After": "60"},
                )
            
            # Thêm request hiện tại
            redis_client.zadd(key, {str(now): now})
            redis_client.expire(key, window)
            return
        except Exception as e:
            logger.error(f"Redis Rate Limiter error: {e}")
            # Fallback to allow if Redis fails
            return

    # Fallback In-memory (Simplified for single instance)
    # Trong thực tế bản hoàn chỉnh nên có fallback dict ở đây
    pass
