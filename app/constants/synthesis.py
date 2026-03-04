"""
Synthesis logic constants.

- Preview synthesis: shown after user completes SYNTHESIS_PREVIEW_MIN_TESTS (e.g. 3).
- Full synthesis: unlocked after user completes between SYNTHESIS_FULL_MIN_TESTS and SYNTHESIS_FULL_MAX_TESTS (e.g. 6–8).
- Synthesis recalculates only when a new test is completed (not on every request).
- Weekly predictions: generated from stored synthesis JSON + timing tags only (not from raw answers).
"""

SYNTHESIS_PREVIEW_MIN_TESTS = 3

SYNTHESIS_FULL_MIN_TESTS = 6
SYNTHESIS_FULL_MAX_TESTS = 8
