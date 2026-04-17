import time
import logging
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)
redis_client = settings.get_redis_client()

def check_and_record_cost(user_id: str, input_tokens: int, output_tokens: int):
    """
    Theo dõi và giới hạn chi phí sử dụng LLM theo ngày dùng Redis.
    """
    today = time.strftime("%Y-%m-%d")
    key = f"cost:{user_id}:{today}"
    budget = settings.daily_budget_usd
    
    # Tính toán chi phí request hiện tại
    # Giả định giá GPT-4o-mini
    current_request_cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    
    if redis_client:
        try:
            current_total = float(redis_client.get(key) or 0)
            
            if current_total + current_request_cost > budget:
                raise HTTPException(
                    status_code=402, 
                    detail=f"Daily budget exceeded (${budget}). Used: ${current_total:.4f}"
                )
            
            # Cập nhật chi phí
            redis_client.incrbyfloat(key, current_request_cost)
            redis_client.expire(key, 86400 * 2) # Giữ 2 ngày để debug
            return
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cost Guard Redis error: {e}")
            return

    # Fallback ghi log nếu không có Redis
    logger.info(f"Cost check for {user_id}: ${current_request_cost:.6f}")
