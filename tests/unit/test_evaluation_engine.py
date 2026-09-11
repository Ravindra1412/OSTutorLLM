"""
tests/test_evaluation_engine.py

Section 22 — Evaluation Tests. Covers every auto-gradable question
type's grading logic directly (no LLM, no Flask app context needed for
most of these — pure function tests over QuizQuestion-shaped objects).
"""

import json
import pytest

from app.quiz.services import evaluation_engine


def _mock_question(question_type, correct_answer, points=1.0, difficulty_level=1):
    class FakeQuestion:
        pass
    q = FakeQuestion()
    q.id = 1
    q.question_type = question_type
    q.correct_answer = json.dumps(correct_answer)
    q.points = points
    q.difficulty_level = difficulty_level
    q.question_text = "test question"
    return q


class TestMCQAndSingleValueTypes:
    def test_mcq_correct(self):
        q = _mock_question("mcq", "Read, execute")
        result = evaluation_engine._evaluate_auto(q, "Read, execute")
        assert result.is_correct is True
        assert result.score_fraction == 1.0

    def test_mcq_incorrect(self):
        q = _mock_question("mcq", "Read, execute")
        result = evaluation_engine._evaluate_auto(q, "Write only")
        assert result.is_correct is False
        assert result.score_fraction == 0.0

    def test_mcq_case_and_whitespace_insensitive(self):
        q = _mock_question("mcq", "Read, execute")
        result = evaluation_engine._evaluate_auto(q, "  READ,   EXECUTE  ")
        assert result.is_correct is True

    def test_true_false(self):
        q = _mock_question("true_false", "true")
        assert evaluation_engine._evaluate_auto(q, "true").is_correct is True
        assert evaluation_engine._evaluate_auto(q, "false").is_correct is False

    def test_command_prediction(self):
        q = _mock_question("command_prediction", "ls -la")
        assert evaluation_engine._evaluate_auto(q, "ls -la").is_correct is True
        assert evaluation_engine._evaluate_auto(q, "ls -l").is_correct is False


class TestFillBlank:
    def test_accepts_any_listed_variant(self):
        q = _mock_question("fill_blank", ["+x", "u+x", "755", "775"])
        assert evaluation_engine._evaluate_auto(q, "+x").is_correct is True
        assert evaluation_engine._evaluate_auto(q, "755").is_correct is True
        assert evaluation_engine._evaluate_auto(q, "wrong").is_correct is False

    def test_single_string_correct_answer(self):
        q = _mock_question("fill_blank", "pwd")
        assert evaluation_engine._evaluate_auto(q, "pwd").is_correct is True


class TestMultiSelect:
    def test_exact_match_full_credit(self):
        q = _mock_question("multi_select", ["a", "b", "c"])
        result = evaluation_engine._evaluate_auto(q, json.dumps(["a", "b", "c"]))
        assert result.is_correct is True
        assert result.score_fraction == 1.0

    def test_partial_selection_partial_credit(self):
        q = _mock_question("multi_select", ["a", "b", "c"])
        result = evaluation_engine._evaluate_auto(q, json.dumps(["a", "b"]))
        assert result.is_correct is False
        assert result.score_fraction == pytest.approx(2 / 3, abs=0.01)

    def test_false_positive_selection_reduces_credit(self):
        """Section 9 — selecting a wrong option in addition to right
        ones should reduce the fraction, not just fail to add to it."""
        q = _mock_question("multi_select", ["a", "b"])
        result = evaluation_engine._evaluate_auto(q, json.dumps(["a", "b", "wrong"]))
        assert result.score_fraction == 0.5  # 2 correct - 1 wrong = 1, over 2 total = 0.5

    def test_score_never_goes_negative(self):
        q = _mock_question("multi_select", ["a"])
        result = evaluation_engine._evaluate_auto(q, json.dumps(["wrong1", "wrong2", "wrong3"]))
        assert result.score_fraction == 0.0


class TestMatching:
    def test_all_pairs_correct(self):
        q = _mock_question("match_the_following", {"0": "1", "1": "0"})
        result = evaluation_engine._evaluate_auto(q, json.dumps({"0": "1", "1": "0"}))
        assert result.is_correct is True
        assert result.score_fraction == 1.0

    def test_half_pairs_correct_partial_credit(self):
        q = _mock_question("match_the_following", {"0": "1", "1": "0"})
        result = evaluation_engine._evaluate_auto(q, json.dumps({"0": "1", "1": "wrong"}))
        assert result.is_correct is False
        assert result.score_fraction == 0.5


class TestOrdering:
    def test_correct_order_full_credit(self):
        q = _mock_question("drag_and_drop", [0, 1, 2])
        result = evaluation_engine._evaluate_auto(q, json.dumps([0, 1, 2]))
        assert result.is_correct is True
        assert result.score_fraction == 1.0

    def test_partially_correct_order_partial_credit(self):
        q = _mock_question("drag_and_drop", [0, 1, 2])
        result = evaluation_engine._evaluate_auto(q, json.dumps([0, 2, 1]))
        assert result.is_correct is False
        assert result.score_fraction == pytest.approx(1 / 3, abs=0.01)


class TestLLMAssistedTypesRouting:
    def test_evaluation_mode_routes_correctly(self):
        from app.quiz import question_types
        assert question_types.evaluation_mode_for("mcq") == "auto"
        assert question_types.evaluation_mode_for("scenario") == "llm"
        assert question_types.evaluation_mode_for("case_study") == "llm"
        assert question_types.evaluation_mode_for("shell_programming") == "llm"
        assert question_types.evaluation_mode_for("error_identification") == "llm"
        assert question_types.evaluation_mode_for("viva") == "manual"

    def test_manual_mode_returns_pending_review(self):
        q = _mock_question("viva", "some rubric")
        result = evaluation_engine.evaluate_answer(q, "student's spoken answer transcript", "Topic")
        assert result.pending_review is True
        assert result.is_correct is False
