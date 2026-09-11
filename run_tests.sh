#!/usr/bin/env bash
# =============================================================================
# run_tests.sh — Part 3.11, Section 19 (Automation)
#
# Single entry point for every testing "type" from Section 1, so a
# student (or a future CI pipeline, Section 25) never has to remember
# raw pytest flags. Usage:
#
#   ./run_tests.sh              # everything except performance (fast, default)
#   ./run_tests.sh unit         # one marker only
#   ./run_tests.sh integration
#   ./run_tests.sh api
#   ./run_tests.sh security
#   ./run_tests.sh frontend
#   ./run_tests.sh performance  # slow — real live-server concurrency tests
#   ./run_tests.sh all          # everything, including performance
#   ./run_tests.sh coverage     # full run + HTML/XML coverage report
# =============================================================================

set -e
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
MODE="${1:-default}"

case "$MODE" in
  default)
    echo "Running full suite (excludes -m performance; see pytest.ini)..."
    $PYTHON_BIN -m pytest tests/ -v
    ;;
  unit|integration|api|security|frontend|performance)
    echo "Running '$MODE' tests only..."
    $PYTHON_BIN -m pytest tests/ -v -m "$MODE"
    ;;
  all)
    echo "Running the ENTIRE suite, including performance (slower)..."
    $PYTHON_BIN -m pytest tests/ -v -m ""
    ;;
  coverage)
    echo "Running full suite with coverage (excludes performance)..."
    $PYTHON_BIN -m pytest tests/ -m "" \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=html:tests/reports/coverage_html \
      --cov-report=xml:tests/reports/coverage.xml
    echo ""
    echo "HTML report: tests/reports/coverage_html/index.html"
    echo "XML report:  tests/reports/coverage.xml"
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Valid modes: default, unit, integration, api, security, frontend, performance, all, coverage"
    exit 1
    ;;
esac
