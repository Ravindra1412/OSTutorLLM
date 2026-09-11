"""
tests/test_hint_engine.py

Section 17 — Hint Engine Tests. Pure unit tests, no Flask app context
or database needed, since app/ai/services/hint_engine.py is
deliberately dependency-free (see its module docstring). This is what
lets the Section 7 workflow enforcement be tested exhaustively and
fast, independent of any LLM provider.
"""

from app.ai.services import hint_engine
from app.ai import config


class TestIntentClassification:
    def test_classifies_plain_attempt(self):
        assert hint_engine.classify_intent("I think it's chmod 755") == hint_engine.INTENT_ATTEMPT

    def test_classifies_hint_request(self):
        assert hint_engine.classify_intent("I don't know, give me a hint") == hint_engine.INTENT_REQUEST_HINT

    def test_classifies_stuck_as_hint_request(self):
        assert hint_engine.classify_intent("I'm stuck on this one") == hint_engine.INTENT_REQUEST_HINT

    def test_classifies_answer_request(self):
        assert hint_engine.classify_intent("just tell me the answer") == hint_engine.INTENT_REQUEST_ANSWER

    def test_classifies_give_up_as_answer_request(self):
        assert hint_engine.classify_intent("I give up") == hint_engine.INTENT_REQUEST_ANSWER


class TestStageProgression:
    """Directly verifies the Section 7 workflow diagram is enforced."""

    def test_diagnostic_advances_to_hint_1_on_attempt(self):
        assert hint_engine.next_stage(config.HINT_STAGE_DIAGNOSTIC, hint_engine.INTENT_ATTEMPT) == 1

    def test_hint_1_advances_to_hint_2(self):
        assert hint_engine.next_stage(1, hint_engine.INTENT_ATTEMPT) == 2

    def test_hint_2_advances_to_hint_3(self):
        assert hint_engine.next_stage(2, hint_engine.INTENT_ATTEMPT) == 3

    def test_hint_3_advances_to_reveal_regardless_of_intent(self):
        """Section 7's final required transition: hints must be
        exhausted before reveal — verified for BOTH intents at stage 3."""
        assert hint_engine.next_stage(3, hint_engine.INTENT_ATTEMPT) == config.HINT_STAGE_REVEAL
        assert hint_engine.next_stage(3, hint_engine.INTENT_REQUEST_HINT) == config.HINT_STAGE_REVEAL

    def test_explicit_answer_request_skips_to_reveal_from_any_stage(self):
        for stage in (0, 1, 2, 3):
            assert hint_engine.next_stage(stage, hint_engine.INTENT_REQUEST_ANSWER) == config.HINT_STAGE_REVEAL

    def test_cannot_skip_hint_stages_via_plain_attempt(self):
        """The critical non-negotiable property: an ordinary attempt at
        stage 0 NEVER jumps straight past hint 1/2/3 to reveal."""
        stage = config.HINT_STAGE_DIAGNOSTIC
        seen_stages = [stage]
        for _ in range(3):
            stage = hint_engine.next_stage(stage, hint_engine.INTENT_ATTEMPT)
            seen_stages.append(stage)
        assert seen_stages == [0, 1, 2, 3]  # every stage visited in order, none skipped

    def test_is_hint_ladder_exhausted(self):
        assert hint_engine.is_hint_ladder_exhausted(3) is True
        assert hint_engine.is_hint_ladder_exhausted(4) is True
        assert hint_engine.is_hint_ladder_exhausted(2) is False

    def test_reset_for_new_question_returns_diagnostic(self):
        assert hint_engine.reset_for_new_question() == config.HINT_STAGE_DIAGNOSTIC
