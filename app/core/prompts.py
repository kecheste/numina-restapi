TEST_RESULT_SYSTEM = """You are a warm, insightful coach who turns assessment data into clear, encouraging results.
You write only valid JSON. No markdown, no code fences, no extra text.
Keep the entire response under 2000 tokens: short sentences, 2-5 items per array."""

TEST_RESULT_USER_TEMPLATE = """Test: {test_title} (category: {category}).
{user_context}

Computed/structured result for this user (use only this; do not invent data):
{input_json}

Return exactly one JSON object with these keys only:
- "title": string, one short catchy title (e.g. "The Reflective Seeker")
- "summary": string, short intro/overview paragraph (2-4 sentences) for the result screen
- "coreTraits": array of 2-5 short strings (bullets or tags)
- "strengths": array of 2-5 short strings (bullets)
- "challenges": array of 2-5 short strings (bullets)
- "spiritualInsight": string, one paragraph spiritual interpretation
- "tryThis": array of 2-4 short strings (practical tips)
- "avoidThis": array of 2-4 short strings (warnings)
- "synchronicities": optional array of objects with "test" and "connection" (if overlaps with other tests exist)

Output only the JSON object, nothing else."""

CHAKRA_PREVIEW_USER_APPENDIX = """
Additionally include these two keys (required for this test):
- "strongestChakra": string, one sentence describing which chakra is currently strongest for this user based on their answers (e.g. "Your energy flows most freely through your Crown Chakra, indicating heightened intuition.")
- "needsRebalancing": string, one sentence describing which chakra most needs rebalancing (e.g. "You may want to bring attention to your Root Chakra, which governs your sense of stability and grounding.")
"""
TEST_RESULT_JSON_KEYS = frozenset({
    "title", "summary", "coreTraits", "strengths", "challenges",
    "spiritualInsight", "tryThis", "avoidThis", "synchronicities",
})
CHAKRA_PREVIEW_JSON_KEYS = frozenset({"strongestChakra", "needsRebalancing"})


SYNTHESIS_SYSTEM = """You are a spiritual and psychological synthesis coach. You weave multiple test results into one coherent portrait.
You write only valid JSON. No markdown, no code fences, no extra text.
Keep each field concise: short paragraphs, 3-6 list items where applicable."""

SYNTHESIS_PREVIEW_USER_TEMPLATE = """The user has completed {count} onboarding tests. Below is the structured data from those results (compact).

{input_json}

Return exactly one JSON object with these keys only:
- "youAre": string, 2-3 sentences describing who they are based on these first tests
- "sureThings": array of 3-5 short strings (traits/patterns that already stand out)
- "identitySummary": string, one short paragraph (emerging identity)
- "growthAreas": array of 2-4 short strings (areas to explore next)
- "nextFocus": string, one sentence suggesting what to do next

Output only the JSON object, nothing else."""

SYNTHESIS_FULL_USER_TEMPLATE = """The user has completed {count} tests. Below is the structured data from all their results (compact).

{input_json}

Return exactly one JSON object with these keys only:
- "youAre": string, 3-5 sentences describing their full portrait across all tests
- "sureThings": array of 5-8 short strings (traits/patterns that appear consistently)
- "identitySummary": string, one rich paragraph (integrated identity)
- "growthAreas": array of 3-5 short strings (areas for growth)
- "nextFocus": string, 1-2 sentences for what to focus on next
- "themes": array of 3-5 short strings (cross-cutting themes)
- "strengths": array of 3-5 short strings (core strengths)
- "shadowPatterns": array of 0-3 short strings (patterns to be aware of, if any)

Output only the JSON object, nothing else."""

SYNTHESIS_PREVIEW_JSON_KEYS = frozenset({"youAre", "sureThings", "identitySummary", "growthAreas", "nextFocus"})
SYNTHESIS_FULL_JSON_KEYS = frozenset({
    "youAre", "sureThings", "identitySummary", "growthAreas", "nextFocus",
    "themes", "strengths", "shadowPatterns",
})


BLUEPRINT_SYSTEM = """You are a warm, insightful astrologer and numerologist. You write only valid JSON. No markdown, no code fences.
Keep each field concise: 1-3 sentences for descriptions."""

ASTROLOGY_BLUEPRINT_USER = """The user's astrology chart (from birth data):
- Sun sign: {sun_sign}
- Moon sign: {moon_sign}
- Rising sign: {rising_sign}
- Element distribution: fire={fire}, earth={earth}, air={air}, water={water}

Return exactly one JSON object with these keys only:
- "sunDescription": string, 1-2 sentences on core personality from their sun sign (personalized, warm)
- "moonDescription": string, 1-2 sentences on emotional self from their moon sign
- "risingDescription": string, 1-2 sentences on how others see them from rising sign
- "cosmicTraitsSummary": string, exactly 4 lines in this format (use the exact emoji at the start of each line, then one value per line derived from their chart):
  Line 1: 🜂 Element: [one of: Water / Earth / Fire / Air — pick the dominant element from their chart]
  Line 2: ☌ Modality: [one of: Fixed / Mutable / Cardinal — from their sun/moon/rising]
  Line 3: ♇ Ruling Planet: [e.g. Pluto, Mars, Venus — main ruling planet(s) for their chart]
  Line 4: 🌠 Most active house: [e.g. 7th – Partnerships — the most emphasized house]

Output only the JSON object, nothing else."""

ASTROLOGY_BLUEPRINT_JSON_KEYS = frozenset({"sunDescription", "moonDescription", "risingDescription", "cosmicTraitsSummary"})

NUMEROLOGY_BLUEPRINT_USER = """The user's numerology (from birth date and name):
- Life path number: {life_path}
- Soul urge number: {soul_urge}

Return exactly one JSON object with this key only:
- "items": array of objects, each with "number" (string, e.g. "7"), "title" (string, e.g. "Life Path"), "description" (string: exactly ONE sentence, maximum 70 characters, personalized for this user). Include at least: Life Path ({life_path}), Soul Urge ({soul_urge}). You may add 1-2 more relevant numbers (e.g. Expression, Birthday) with one short sentence each (max 70 chars). Maximum 5 items.

Output only the JSON object, nothing else."""

NUMEROLOGY_BLUEPRINT_JSON_KEYS = frozenset({"items"})
