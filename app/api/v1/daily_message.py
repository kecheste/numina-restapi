"""
Daily message: personalized per user using mostSureThings + profile context (LLM, cached in Redis).
Falls back to static day-of-month list when the user has no synthesis data or LLM is unavailable.
"""

import json
import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_optional_current_user
from app.core.redis import cache_get
from app.db.models.user import User as UserModel
from app.schemas.daily_message import DailyMessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["daily-message"])

# ── Static fallback messages (index 0 = 1st of month, rotates by day-of-month) ──
DAILY_MESSAGES: list[tuple[str, str]] = [
    ("Today carries a gentle turning energy — a chance to align with what matters. Let your intuition lead; the mind can follow.", "Your silence speaks in sacred language."),
    ("The cosmos favors reflection over action today. Stillness will reveal more than effort. Trust the quiet.", "In stillness, the soul finds its voice."),
    ("A turning point of light and inner clarity is near. Deep waters flow steadily; you might feel a quiet pull to observe more than act.", "The unseen guides the seen."),
    ("Ground yourself in small, tangible steps. Earth energy supports patience and persistence today.", "Roots before branches."),
    ("Creative energy is available but scattered. Choose one thing to complete; it will matter more than many starts.", "One focused step outweighs a hundred glances."),
    ("Relationships and balance are in focus. Someone may need your calm presence. Give without losing yourself.", "Balance is not splitting in half — it is holding both."),
    ("Spiritual curiosity is high. A book, a walk, or a moment of silence could bring a needed insight.", "Seek and you shall find — in the quiet."),
    ("Power and responsibility walk together today. Use your influence with care; others are watching and learning.", "True power serves."),
    ("Compassion for yourself is the theme. You have done enough; rest is not laziness.", "Rest is part of the work."),
    ("Clarity may come through a conversation or a dream. Pay attention to symbols and déjà vu.", "The soul speaks in symbols."),
    ("Transformation is in the air. Something old can be released to make room for the new. Don't force — allow.", "Letting go is also receiving."),
    ("Service to others will feed your spirit today. A small act of kindness will echo.", "We rise by lifting others."),
    ("Logic and intuition can work together. Balance analysis with a gut check before deciding.", "The head and heart share one compass."),
    ("Freedom and change are calling. It's okay to want something different. Explore without burning bridges.", "Change begins with permission."),
    ("Nurturing and home energy are strong. Tend to your space or your people; both need care.", "Home is where the heart can rest."),
    ("Depth over breadth. One meaningful exchange will matter more than many surface ones.", "Depth is a kind of magic."),
    ("Hope and vision are available. Write down a wish or a goal; the act of naming helps it take shape.", "What we name, we can nurture."),
    ("Shadow and light both belong. Acknowledging a difficult feeling can soften its grip.", "Light is not the absence of dark — it is presence."),
    ("Connection to nature or body will ground you. Move, breathe, or step outside.", "The body remembers what the mind forgets."),
    ("Communication may be charged. Speak clearly and listen fully; misunderstandings are likely today.", "Listen first; words follow."),
    ("Inner sight is sharp. Trust a first impression or a sudden knowing.", "Intuition is intelligence."),
    ("Completion energy: one cycle is ending so another can begin. Tie up a loose end.", "Every end is a beginning in disguise."),
    ("Expansion and learning are favored. Say yes to an opportunity that stretches you slightly.", "Growth lives just outside comfort."),
    ("Solitude can restore. It's okay to decline plans and recharge alone.", "Alone is not lonely."),
    ("Partnership and fairness are in focus. Seek win-win; compromise without losing your core.", "Together does not mean dissolved."),
    ("Transformation through release. Something — a habit, a belief, a grudge — is ready to go.", "Release is a form of love."),
    ("Wisdom and teaching flow. Share what you know; someone is ready to hear it.", "We teach what we need to learn."),
    ("Ambition is supported, but check that it aligns with your values. Success without meaning is empty.", "Purpose gives success its soul."),
    ("Emotions may run deep. Allow them without drama; they are data, not destiny.", "Feel it; don't become it."),
    ("Integration day: pieces of your story can click into place. Look for patterns.", "The pattern is the message."),
    ("Tomorrow's energy is already stirring. Set an intention before sleep; the unconscious will work on it.", "The night is a partner, not a blank."),
]


def _static_message() -> DailyMessageResponse:
    """Return the day-of-month static message."""
    today = date.today()
    index = (today.day - 1) % len(DAILY_MESSAGES)
    message, quote = DAILY_MESSAGES[index]
    return DailyMessageResponse(message=message, quote=quote)


def _seconds_until_midnight() -> int:
    """Seconds remaining until midnight UTC (minimum 60s)."""
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    # advance to tomorrow midnight
    from datetime import timedelta
    midnight += timedelta(days=1)
    remaining = int((midnight - now).total_seconds())
    return max(remaining, 60)


async def _generate_personalized_message(user: UserModel, completed_count: int) -> DailyMessageResponse | None:
    """Call gpt-4o-mini to generate a personalized daily message. Returns None on failure."""
    if not settings.openai_api_key:
        return None

    from app.core.prompts import DAILY_MESSAGE_SYSTEM, DAILY_MESSAGE_USER_TEMPLATE
    from app.worker.helpers import zodiac_from_date

    most_sure = user.most_sure_things or []
    chips_str = ", ".join(most_sure) if most_sure else "not yet available"
    mbti = user.mbti_type or "unknown"
    zodiac = "unknown"
    if user.birth_month and user.birth_day:
        zodiac = zodiac_from_date(user.birth_month, user.birth_day)
    life_path = str(user.life_path_number) if user.life_path_number else "unknown"

    user_prompt = DAILY_MESSAGE_USER_TEMPLATE.format(
        most_sure_things=chips_str,
        mbti_type=mbti,
        zodiac=zodiac,
        life_path=life_path,
        count=completed_count,
    )

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": DAILY_MESSAGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=250,
            temperature=0.7,
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
        msg = str(data.get("message", "")).strip()
        quote = str(data.get("quote", "")).strip()
        if msg and quote:
            return DailyMessageResponse(message=msg, quote=quote)
    except Exception as e:
        logger.warning("Daily message LLM call failed for user_id=%s: %s", user.id, e)

    return None


@router.get("/daily-message", response_model=DailyMessageResponse)
async def get_daily_message(
    current_user: UserModel | None = Depends(get_optional_current_user),
) -> DailyMessageResponse:
    """
    Return today's daily message and quote.
    - Authenticated users with synthesis data get a personalized, LLM-generated message.
      Cached in Redis (key: daily_msg:{user_id}:{YYYY-MM-DD}) with DB fallback.
    - All other cases fall back to the static day-of-month list.
    """
    if current_user is None:
        return _static_message()

    # 1. Try Snapshot from User model
    snapshot = current_user.soul_snapshot
    today_str = date.today().isoformat()
    
    if snapshot:
        # If it's today, return it
        if snapshot.get("daily_date") == today_str:
            return DailyMessageResponse(
                message=snapshot.get("daily_message", ""),
                quote=snapshot.get("daily_quote", ""),
            )
        
        # If it's a new day, we should ideally refresh it.
        # For now, we'll try to refresh it synchronously if they have enough data, 
        # or just trigger a background refresh and return static/old context.
        try:
            from app.db.session import AsyncSessionLocal
            from app.db.models.user import User as _User
            from app.worker.soul_snapshot import generate_soul_snapshot
            async with AsyncSessionLocal() as session:
                await generate_soul_snapshot(session, current_user.id, refresh_pulse_only=True)
                refreshed = await session.get(_User, current_user.id)
                if refreshed:
                    snapshot = refreshed.soul_snapshot
            if snapshot and snapshot.get("daily_date") == today_str:
                return DailyMessageResponse(
                    message=snapshot.get("daily_message", ""),
                    quote=snapshot.get("daily_quote", ""),
                )
        except Exception as e:
            logger.warning("Synchronous snapshot refresh failed for user_id=%s: %s", current_user.id, e)

    # 2. Try legacy Redis cache (migration period)
    redis_key = f"daily_msg:{current_user.id}:{today_str}"
    cached = await cache_get(redis_key)
    if cached:
        return DailyMessageResponse(
            message=cached.get("message", ""),
            quote=cached.get("quote", ""),
        )

    # 3. Fallback to LLM-generated message (legacy logic)
    # This also helps for users who don't have a snapshot yet but have synthesis.
    if current_user.most_sure_things:
        result = await _generate_personalized_message(current_user, 0)
        if result:
            return result

    # 4. All else fails → static
    return _static_message()
