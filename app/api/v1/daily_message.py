"""
Daily message: static list keyed by day-of-month. No LLM — zero token cost.
Returns one message + quote per day for the My Soul screen.
"""

from datetime import date

from fastapi import APIRouter

from app.schemas.daily_message import DailyMessageResponse

router = APIRouter(tags=["daily-message"])

# 31 pre-written messages (index 0 = 1st of month, etc.). Rotates by day-of-month.
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
    ("Transformation is in the air. Something old can be released to make room for the new. Don’t force — allow.", "Letting go is also receiving."),
    ("Service to others will feed your spirit today. A small act of kindness will echo.", "We rise by lifting others."),
    ("Logic and intuition can work together. Balance analysis with a gut check before deciding.", "The head and heart share one compass."),
    ("Freedom and change are calling. It’s okay to want something different. Explore without burning bridges.", "Change begins with permission."),
    ("Nurturing and home energy are strong. Tend to your space or your people; both need care.", "Home is where the heart can rest."),
    ("Depth over breadth. One meaningful exchange will matter more than many surface ones.", "Depth is a kind of magic."),
    ("Hope and vision are available. Write down a wish or a goal; the act of naming helps it take shape.", "What we name, we can nurture."),
    ("Shadow and light both belong. Acknowledging a difficult feeling can soften its grip.", "Light is not the absence of dark — it is presence."),
    ("Connection to nature or body will ground you. Move, breathe, or step outside.", "The body remembers what the mind forgets."),
    ("Communication may be charged. Speak clearly and listen fully; misunderstandings are likely today.", "Listen first; words follow."),
    ("Inner sight is sharp. Trust a first impression or a sudden knowing.", "Intuition is intelligence."),
    ("Completion energy: one cycle is ending so another can begin. Tie up a loose end.", "Every end is a beginning in disguise."),
    ("Expansion and learning are favored. Say yes to an opportunity that stretches you slightly.", "Growth lives just outside comfort."),
    ("Solitude can restore. It’s okay to decline plans and recharge alone.", "Alone is not lonely."),
    ("Partnership and fairness are in focus. Seek win-win; compromise without losing your core.", "Together does not mean dissolved."),
    ("Transformation through release. Something — a habit, a belief, a grudge — is ready to go.", "Release is a form of love."),
    ("Wisdom and teaching flow. Share what you know; someone is ready to hear it.", "We teach what we need to learn."),
    ("Ambition is supported, but check that it aligns with your values. Success without meaning is empty.", "Purpose gives success its soul."),
    ("Emotions may run deep. Allow them without drama; they are data, not destiny.", "Feel it; don’t become it."),
    ("Integration day: pieces of your story can click into place. Look for patterns.", "The pattern is the message."),
    ("Tomorrow’s energy is already stirring. Set an intention before sleep; the unconscious will work on it.", "The night is a partner, not a blank."),
]


@router.get("/daily-message", response_model=DailyMessageResponse)
async def get_daily_message() -> DailyMessageResponse:
    """
    Return today's daily message and quote. Keyed by day-of-month (1–31).
    No auth; same message for everyone. No LLM — zero token cost.
    """
    today = date.today()
    index = (today.day - 1) % len(DAILY_MESSAGES)
    message, quote = DAILY_MESSAGES[index]
    return DailyMessageResponse(message=message, quote=quote)
