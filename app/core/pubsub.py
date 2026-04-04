import json
import logging
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

async def broadcast_user_update(user_id: int, event_type: str, data: dict) -> None:
    """Broadcast a real-time event to a user's WebSocket channel via Redis PubSub."""
    redis = get_redis()
    if redis is None:
        logger.warning(f"Redis not available to broadcast for user {user_id}")
        return
        
    channel = f"user_updates:{user_id}"
    message = {
        "type": event_type,
        "data": data
    }
    
    try:
        await redis.publish(channel, json.dumps(message))
        logger.info(f"Broadcasted to {channel}: {event_type}")
    except Exception as e:
        logger.error(f"Failed to publish to redis {channel}: {e}")
