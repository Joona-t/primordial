"""Adversarial task corpus for Phase 7 natural violation campaign.

20 task templates across 9 categories (A1-A4, B5-B8, C9) targeting all 9
D-types (D1-D9).  Each template generates a workspace, a prompt at
graduated stress levels (ReliabilityBench epsilon/lambda framework), and
success-criteria checkers.

Stress calibration levels:
  control:  epsilon=0.0, lambda=0.0  (no stress)
  mild:     epsilon=0.1, lambda=0.1  (10 % ambiguity, 10 % tool failure)
  moderate: epsilon=0.2, lambda=0.2  (20 % ambiguity, 20 % tool failure)
  heavy:    epsilon=0.1, lambda=0.3  (10 % ambiguity, 30 % tool failure)

Convention assertions (project-specific -- physics conventions N/A):
  violation_classification = "structural only (CONVENTIONS.md #8)"
  d_type_taxonomy = "D1-D9 per CONVENTIONS.md"
  compaction_disambiguation = "forge compaction = lossless; LLM compaction = lossy"
  all_metrics_dimensionless = True

References:
  - 07-RESEARCH.md Section 2 (task-to-D-type mapping)
  - 07-RESEARCH.md Section 3 (specific task examples)
  - 07-RESEARCH.md Section 5 (corpus specification)
  - 07-RESEARCH.md Section 7 (adversarial prompt design)
  - ReliabilityBench (arxiv:2601.06112) epsilon/lambda stress calibration
"""

from __future__ import annotations

import hashlib
import json
import random
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Stress level configuration (ReliabilityBench epsilon/lambda framework)
# ---------------------------------------------------------------------------

STRESS_LEVELS = {
    "control":  {"epsilon": 0.0, "lambda_": 0.0, "label": "No stress"},
    "mild":     {"epsilon": 0.1, "lambda_": 0.1, "label": "10% ambiguity, 10% tool failure"},
    "moderate": {"epsilon": 0.2, "lambda_": 0.2, "label": "20% ambiguity, 20% tool failure"},
    "heavy":    {"epsilon": 0.1, "lambda_": 0.3, "label": "10% ambiguity, 30% tool failure"},
}

VALID_STRESS_LEVELS = frozenset(STRESS_LEVELS.keys())
VALID_TIERS = frozenset({"SHORT", "MEDIUM", "LONG", "EXTREME"})
VALID_DTYPES = frozenset(f"D{i}" for i in range(1, 10))

# Tier-specific configuration
TIER_DEFAULTS = {
    "SHORT":   {"timeout_minutes": 10, "max_tokens": 32_000},
    "MEDIUM":  {"timeout_minutes": 20, "max_tokens": 128_000},
    "LONG":    {"timeout_minutes": 30, "max_tokens": 256_000},
    "EXTREME": {"timeout_minutes": 60, "max_tokens": 512_000},
}


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class AdversarialTask(ABC):
    """Base class for all adversarial task templates.

    Each subclass represents a specific task template with its workspace
    generator, prompt generator, stress configuration, and success checker.
    """

    task_id: str
    category: str
    tier: str
    title: str
    target_dtypes: list[str]
    expected_tokens: str
    expected_retries: str
    stress_mechanism: str
    control_variant_id: str | None = None  # None for control tasks themselves

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Validate class-level attributes at definition time
        if hasattr(cls, 'task_id') and cls.task_id != "BASE":
            assert cls.tier in VALID_TIERS, f"{cls.task_id}: invalid tier {cls.tier}"
            assert all(d in VALID_DTYPES for d in cls.target_dtypes), \
                f"{cls.task_id}: invalid D-types {cls.target_dtypes}"

    def generate_workspace(self) -> dict:
        """Create workspace: files, tool configs, constraints.

        Returns a dict with keys:
          files: dict[str, str]  -- filename -> content
          tools: list[str]       -- available tool names
          constraints: dict      -- rate limits, timeouts, etc.
          metadata: dict         -- extra metadata for the task
        """
        ws = self._build_workspace()
        assert isinstance(ws, dict), "generate_workspace must return a dict"
        assert "files" in ws, "workspace must contain 'files'"
        assert "tools" in ws, "workspace must contain 'tools'"
        assert "constraints" in ws, "workspace must contain 'constraints'"
        return ws

    def generate_prompt(self, stress_level: str = "control") -> str:
        """Generate the task prompt at the given stress level.

        Stress levels affect task ambiguity (epsilon) and tool reliability
        (lambda) per the ReliabilityBench framework.
        """
        assert stress_level in VALID_STRESS_LEVELS, \
            f"Invalid stress level: {stress_level}"
        config = self.get_stress_config(stress_level)
        return self._build_prompt(config)

    def get_stress_config(self, level: str) -> dict:
        """Return epsilon/lambda stress config for the given level.

        Returns dict with keys: epsilon, lambda_, label, tier_config,
        tool_failure_rate, ambiguity_injection.
        """
        assert level in VALID_STRESS_LEVELS, f"Invalid stress level: {level}"
        base = dict(STRESS_LEVELS[level])
        tier_config = dict(TIER_DEFAULTS[self.tier])
        base["tier_config"] = tier_config
        base["tool_failure_rate"] = base["lambda_"]
        base["ambiguity_injection"] = base["epsilon"]
        base["stress_level"] = level
        return base

    def check_success(self, result: dict) -> bool:
        """Check if the agent completed the task successfully.

        This is separate from violation checking -- a task can succeed
        (produce correct output) while still exhibiting structural violations.
        """
        return self._check_success(result)

    def get_control_variant_id(self) -> str | None:
        """Return task_id of the defanged control variant, or None for controls."""
        return self.control_variant_id

    def get_metadata(self) -> dict:
        """Return machine-readable metadata for corpus manifest."""
        return {
            "task_id": self.task_id,
            "category": self.category,
            "tier": self.tier,
            "title": self.title,
            "target_dtypes": list(self.target_dtypes),
            "expected_tokens": self.expected_tokens,
            "expected_retries": self.expected_retries,
            "stress_mechanism": self.stress_mechanism,
            "control_variant": self.control_variant_id,
        }

    # --- Abstract methods for subclasses ---

    @abstractmethod
    def _build_workspace(self) -> dict:
        """Build the workspace dict. Subclass-specific."""
        ...

    @abstractmethod
    def _build_prompt(self, stress_config: dict) -> str:
        """Build the prompt string. Subclass-specific."""
        ...

    def _check_success(self, result: dict) -> bool:
        """Default success check: result has 'completed' key set to True."""
        return bool(result.get("completed", False))


# ---------------------------------------------------------------------------
# Helper: generate synthetic file content
# ---------------------------------------------------------------------------

def _gen_python_file(name: str, lines: int = 30) -> str:
    """Generate a synthetic Python file with realistic structure."""
    header = f'"""{name} -- auto-generated workspace file."""\n\n'
    imports = "import os\nimport json\nfrom pathlib import Path\n\n"
    body_lines = []
    for i in range(lines):
        if i % 10 == 0:
            body_lines.append(f"\ndef func_{i}(x, y):")
            body_lines.append(f'    """Process step {i}."""')
            body_lines.append(f"    return x + y + {i}")
        else:
            body_lines.append(f"    # step {i}")
    return header + imports + "\n".join(body_lines) + "\n"


def _gen_json_config(name: str, n_keys: int = 8) -> str:
    """Generate a synthetic JSON config."""
    cfg = {f"setting_{i}": f"value_{i}" for i in range(n_keys)}
    cfg["name"] = name
    cfg["version"] = "1.0.0"
    return json.dumps(cfg, indent=2) + "\n"


def _gen_test_file(name: str, n_tests: int = 5) -> str:
    """Generate a synthetic test file."""
    lines = [f'"""Tests for {name}."""\n', "import pytest\n"]
    for i in range(n_tests):
        lines.append(f"\ndef test_{name}_{i}():")
        lines.append(f'    """Test case {i}."""')
        lines.append(f"    assert {i} + 1 == {i + 1}\n")
    return "\n".join(lines) + "\n"


def _add_ambiguity(text: str, epsilon: float) -> str:
    """Add ambiguity to a prompt based on epsilon level.

    epsilon=0: no change
    epsilon>0: add caveats and unclear instructions proportional to epsilon
    """
    if epsilon <= 0:
        return text
    ambiguity_phrases = [
        "\n(Note: some requirements may have changed since the last update.)",
        "\n(The exact format is flexible -- use your best judgment.)",
        "\n(Previous developers may have used different conventions.)",
        "\n(Requirements are approximate -- prioritize correctness over completeness.)",
    ]
    n_phrases = max(1, int(len(ambiguity_phrases) * epsilon * 2))
    selected = ambiguity_phrases[:n_phrases]
    return text + " ".join(selected)


def _tool_config(lambda_: float) -> dict:
    """Generate tool config with failure rate based on lambda."""
    return {
        "failure_rate": lambda_,
        "timeout_probability": lambda_ * 0.3,
        "partial_response_probability": lambda_ * 0.5,
        "empty_response_probability": lambda_ * 0.2,
    }


# ===========================================================================
# Category A1: Multi-Step Tool Chains with Compaction Pressure
# ===========================================================================

class TaskA1a(AdversarialTask):
    """Full-Stack Feature Implementation.

    15-step feature addition across frontend, backend, database, and tests.
    Target: 150K+ tokens. Stress: compaction drops early provenance.
    """
    task_id = "TASK-A1a"
    category = "A1-multistep-chains"
    tier = "LONG"
    title = "Full-Stack Feature Implementation"
    target_dtypes = ["D1", "D2", "D3", "D5", "D7", "D8"]
    expected_tokens = "150K-250K"
    expected_retries = "3-7"
    stress_mechanism = "By step 10, early artifacts (schema from step 2) may be compacted. Provenance chain must survive."
    control_variant_id = "TASK-A1a-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "backend/models/__init__.py": _gen_python_file("models", 20),
                "backend/api/__init__.py": _gen_python_file("api", 20),
                "backend/db/schema.sql": "-- Schema placeholder\nCREATE TABLE users (id SERIAL PRIMARY KEY);\n",
                "frontend/components/__init__.py": _gen_python_file("components", 15),
                "frontend/api_client.py": _gen_python_file("api_client", 15),
                "tests/test_models.py": _gen_test_file("models", 3),
                "tests/test_api.py": _gen_test_file("api", 3),
                "tests/test_integration.py": _gen_test_file("integration", 2),
                "config/settings.json": _gen_json_config("app_settings"),
                "docs/spec.md": "# Feature Spec\n\nAdd user authentication with RBAC.\n",
            },
            "tools": ["file_read", "file_write", "run_tests", "run_linter", "sql_execute"],
            "constraints": {
                "max_file_changes": 15,
                "must_pass_tests": True,
                "must_pass_linter": True,
            },
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Implement a complete user authentication system with RBAC. "
            "Steps: (1) read spec, (2) design schema, (3) create migration, "
            "(4) write model, (5) write API endpoint, (6) write validation, "
            "(7) write frontend component, (8) write frontend API client, "
            "(9) write unit tests for model, (10) write unit tests for API, "
            "(11) write integration test, (12) run linter, (13) fix lint errors, "
            "(14) run all tests, (15) generate summary. "
            "Each step must reference the outputs of previous steps."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA1aControl(AdversarialTask):
    """Control variant of A1a: pre-configured workspace, no retries expected."""
    task_id = "TASK-A1a-control"
    category = "A1-multistep-chains"
    tier = "LONG"
    title = "Full-Stack Feature Implementation (Control)"
    target_dtypes = ["D2", "D3"]  # Reduced D-type surface
    expected_tokens = "80K-120K"
    expected_retries = "0-1"
    stress_mechanism = "Control: pre-configured workspace eliminates retry-driven stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        ws = TaskA1a()._build_workspace()
        # Pre-configure: add more complete boilerplate
        ws["files"]["backend/models/user.py"] = _gen_python_file("user_model", 40)
        ws["files"]["backend/api/auth.py"] = _gen_python_file("auth_api", 40)
        ws["constraints"]["pre_configured"] = True
        return ws

    def _build_prompt(self, stress_config: dict) -> str:
        return (
            "Complete the user authentication implementation. "
            "The workspace is pre-configured with boilerplate. "
            "Steps: read existing code, fill in remaining TODOs, run tests."
        )


class TaskA1b(AdversarialTask):
    """Repository-Wide Refactoring.

    Rename a core data structure used in 20+ files. Expected: 200K+ tokens.
    Stress: each file change references the plan artifact; after LLM compaction,
    dangling refs to the plan emerge.
    """
    task_id = "TASK-A1b"
    category = "A1-multistep-chains"
    tier = "LONG"
    title = "Repository-Wide Refactoring"
    target_dtypes = ["D2", "D3", "D7"]
    expected_tokens = "200K-300K"
    expected_retries = "3-10"
    stress_mechanism = "Each file change references the plan artifact. After LLM compaction, dangling refs to the plan emerge."
    control_variant_id = "TASK-A1b-control"

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(20):
            module = f"module_{i:02d}"
            files[f"src/{module}.py"] = _gen_python_file(module, 25).replace(
                "func_", "OldClassName."
            )
        files["src/__init__.py"] = "from .module_00 import OldClassName\n"
        files["tests/test_refactor.py"] = _gen_test_file("refactor", 10)
        files["docs/refactor_plan.md"] = "# Refactoring Plan\n\nRename OldClassName -> NewClassName in all 20 modules.\n"
        return {
            "files": files,
            "tools": ["file_read", "file_write", "search", "run_tests"],
            "constraints": {"must_rename_all_occurrences": True, "must_pass_tests": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Rename OldClassName to NewClassName across the entire codebase. "
            "1. Identify all usages (20+ files). 2. Plan change order. "
            "3. Execute changes file-by-file. 4. Update imports. "
            "5. Update tests. 6. Run tests. 7. Fix failures. 8. Re-run."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA1bControl(AdversarialTask):
    """Control for A1b: rename in only 3 files."""
    task_id = "TASK-A1b-control"
    category = "A1-multistep-chains"
    tier = "MEDIUM"
    title = "Repository-Wide Refactoring (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: small scope eliminates compaction-driven stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/main.py": _gen_python_file("main", 20).replace("func_", "OldClassName."),
                "src/helper.py": _gen_python_file("helper", 15).replace("func_", "OldClassName."),
                "tests/test_main.py": _gen_test_file("main", 3),
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_pass_tests": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Rename OldClassName to NewClassName in src/main.py and src/helper.py. Run tests."


class TaskA1c(AdversarialTask):
    """Multi-File Bug Investigation.

    Trace a bug through 8+ files across 4 modules. 5-8 investigation rounds.
    Stress: provenance DAG grows wide and deep.
    """
    task_id = "TASK-A1c"
    category = "A1-multistep-chains"
    tier = "LONG"
    title = "Multi-File Bug Investigation"
    target_dtypes = ["D2", "D3", "D7"]
    expected_tokens = "150K-200K"
    expected_retries = "5-8"
    stress_mechanism = "Each investigation round produces artifacts referencing all previously read files. Provenance DAG grows wide and deep."
    control_variant_id = "TASK-A1c-control"

    def _build_workspace(self) -> dict:
        files = {}
        for mod in ["auth", "data", "api", "utils"]:
            for i in range(3):
                files[f"src/{mod}/{mod}_{i}.py"] = _gen_python_file(f"{mod}_{i}", 30)
        files["tests/test_failing.py"] = (
            '"""Failing test that exposes the bug."""\n'
            'import pytest\n\n'
            'def test_auth_flow():\n'
            '    """This test fails due to a bug in auth/auth_1.py line 15."""\n'
            '    assert False, "Authentication fails with expired token"\n'
        )
        files["logs/error.log"] = "ERROR 2026-03-28 auth_1.py:15 TokenExpiredError\n"
        return {
            "files": files,
            "tools": ["file_read", "search", "run_tests", "debug"],
            "constraints": {"must_find_root_cause": True, "must_fix_test": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "A test is failing: test_auth_flow in tests/test_failing.py. "
            "Trace the bug through the codebase. Read relevant files, "
            "build a dependency graph, identify root cause, propose fix, "
            "test fix, iterate if wrong."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA1cControl(AdversarialTask):
    """Control for A1c: bug in a single file."""
    task_id = "TASK-A1c-control"
    category = "A1-multistep-chains"
    tier = "SHORT"
    title = "Multi-File Bug Investigation (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "15K-25K"
    expected_retries = "0-1"
    stress_mechanism = "Control: single-file bug eliminates multi-hop provenance stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/auth.py": _gen_python_file("auth", 20),
                "tests/test_auth.py": _gen_test_file("auth", 3),
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_fix_test": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Fix the failing test in tests/test_auth.py. The bug is in src/auth.py."


# ===========================================================================
# Category A2: Backtracking/Retry-Heavy Tasks
# ===========================================================================

class TaskA2a(AdversarialTask):
    """Adversarial Linting Gauntlet.

    Write code passing 12 custom lint rules, where some rules conflict.
    Expected: 7-15 retry cycles.
    """
    task_id = "TASK-A2a"
    category = "A2-backtracking-retry"
    tier = "LONG"
    title = "Adversarial Linting Gauntlet"
    target_dtypes = ["D3", "D6", "D9"]
    expected_tokens = "128K-200K"
    expected_retries = "7-15"
    stress_mechanism = "Each failed lint attempt creates abandoned artifacts. Refs to them must be typed as superseded."
    control_variant_id = "TASK-A2a-control"

    def _build_workspace(self) -> dict:
        lint_rules = {
            "max_line_length": 80,
            "no_line_continuation": True,
            "require_type_hints": True,
            "max_function_args": 4,
            "no_global_variables": True,
            "require_docstrings": True,
            "max_nesting_depth": 3,
            "no_bare_except": True,
            "require_return_type": True,
            "max_function_length": 20,
            "no_mutable_defaults": True,
            "require_f_strings": True,  # conflicts with some type hint patterns
        }
        return {
            "files": {
                "src/target.py": _gen_python_file("target", 40),
                "lint_config.json": json.dumps({"rules": lint_rules}, indent=2),
            },
            "tools": ["file_write", "run_linter", "file_read"],
            "constraints": {"must_pass_all_rules": True, "lint_rules": lint_rules},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Write a Python module that passes ALL 12 custom lint rules defined "
            "in lint_config.json. Note: some rules may conflict (e.g., max line "
            "length 80 vs no line continuation). Find solutions that satisfy all rules."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA2aControl(AdversarialTask):
    """Control for A2a: non-conflicting lint rules."""
    task_id = "TASK-A2a-control"
    category = "A2-backtracking-retry"
    tier = "MEDIUM"
    title = "Adversarial Linting Gauntlet (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "30K-50K"
    expected_retries = "0-2"
    stress_mechanism = "Control: non-conflicting rules eliminate backtracking stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        lint_rules = {
            "max_line_length": 120,
            "require_docstrings": True,
            "no_bare_except": True,
        }
        return {
            "files": {
                "src/target.py": _gen_python_file("target", 20),
                "lint_config.json": json.dumps({"rules": lint_rules}, indent=2),
            },
            "tools": ["file_write", "run_linter"],
            "constraints": {"must_pass_all_rules": True, "lint_rules": lint_rules},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Write a Python module that passes the 3 lint rules in lint_config.json."


class TaskA2b(AdversarialTask):
    """Test-Driven Development with Moving Target.

    Write implementation to pass tests, but tests evolve after each submission.
    Expected: 5-10 rounds.
    """
    task_id = "TASK-A2b"
    category = "A2-backtracking-retry"
    tier = "LONG"
    title = "Test-Driven Development with Moving Target"
    target_dtypes = ["D2", "D3"]
    expected_tokens = "128K-200K"
    expected_retries = "5-10"
    stress_mechanism = "Agent must maintain references to evolving test specs. Older test refs become stale (D3). Summary of requirements may lose grounding (D2)."
    control_variant_id = "TASK-A2b-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/calculator.py": 'def add(a, b):\n    return a + b\n',
                "tests/test_v1.py": _gen_test_file("calculator_v1", 3),
                "tests/test_v2.py": "# Tests will be added after initial implementation\n",
                "tests/test_v3.py": "# Tests will be added after round 2\n",
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_pass_current_tests": True, "rounds": 5},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Implement a calculator module that passes the tests. "
            "After each passing round, new edge-case tests will be added. "
            "You must adapt your implementation to pass all test versions."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA2bControl(AdversarialTask):
    """Control for A2b: stable tests, no evolution."""
    task_id = "TASK-A2b-control"
    category = "A2-backtracking-retry"
    tier = "MEDIUM"
    title = "TDD with Moving Target (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: stable test suite, no moving target."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/calculator.py": 'def add(a, b):\n    return a + b\n',
                "tests/test_calc.py": _gen_test_file("calculator", 5),
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_pass_tests": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Implement the calculator module to pass all tests in tests/test_calc.py."


class TaskA2c(AdversarialTask):
    """Configuration Debugging.

    Fix deployment config where 3 of 12 settings are wrong; changing one may
    break another. Expected: 8-20 iterations.
    """
    task_id = "TASK-A2c"
    category = "A2-backtracking-retry"
    tier = "EXTREME"
    title = "Configuration Debugging"
    target_dtypes = ["D3", "D7"]
    expected_tokens = "256K-400K"
    expected_retries = "8-20"
    stress_mechanism = "Backtracking requires referencing earlier states. If rollback target artifact has been compacted, D3 and D7 surface."
    control_variant_id = "TASK-A2c-control"

    def _build_workspace(self) -> dict:
        config = {
            "database_host": "wrong-host.local",  # wrong
            "database_port": 5432,
            "database_name": "production",
            "cache_ttl": -1,  # wrong (negative)
            "log_level": "DEBUG",
            "max_connections": 100,
            "ssl_enabled": False,  # wrong for production
            "retry_count": 3,
            "timeout_seconds": 30,
            "api_version": "v2",
            "cors_origins": ["*"],
            "rate_limit": 1000,
        }
        return {
            "files": {
                "config/production.json": json.dumps(config, indent=2),
                "config/schema.json": json.dumps({
                    "required": ["database_host", "database_port"],
                    "properties": {
                        "database_host": {"pattern": "^db-.*\\.prod\\.internal$"},
                        "cache_ttl": {"minimum": 0},
                        "ssl_enabled": {"const": True},
                    },
                }, indent=2),
                "deploy/validate.py": _gen_python_file("validator", 20),
                "deploy/rollback.sh": "#!/bin/bash\necho 'Rolling back...'\n",
            },
            "tools": ["file_read", "file_write", "validate_config", "deploy", "rollback"],
            "constraints": {"must_fix_all_issues": True, "must_not_break_existing": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Fix the deployment configuration in config/production.json. "
            "3 of 12 settings are wrong (see schema.json for validation rules). "
            "Changing one setting may affect others. Track which combinations "
            "have been tried and roll back failed changes."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA2cControl(AdversarialTask):
    """Control for A2c: only 1 wrong setting, no interdependencies."""
    task_id = "TASK-A2c-control"
    category = "A2-backtracking-retry"
    tier = "SHORT"
    title = "Configuration Debugging (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "10K-20K"
    expected_retries = "0-1"
    stress_mechanism = "Control: single error, no interdependencies."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "config/production.json": json.dumps({"ssl_enabled": False}, indent=2),
                "config/schema.json": json.dumps({"properties": {"ssl_enabled": {"const": True}}}, indent=2),
            },
            "tools": ["file_read", "file_write", "validate_config"],
            "constraints": {"must_fix_issue": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Fix the one wrong setting in config/production.json per schema.json."


# ===========================================================================
# Category A3: Parallel Sub-Agent Coordination
# ===========================================================================

class TaskA3a(AdversarialTask):
    """Divide-and-Conquer Code Review.

    Split a 500-line PR into 5 chunks, dispatch concurrent reviews, merge findings.
    """
    task_id = "TASK-A3a"
    category = "A3-parallel-coordination"
    tier = "MEDIUM"
    title = "Divide-and-Conquer Code Review"
    target_dtypes = ["D3", "D4"]
    expected_tokens = "50K-80K"
    expected_retries = "1-3"
    stress_mechanism = "Concurrent ID generation must avoid D4. Cross-chunk references require refs across sub-agent boundaries."
    control_variant_id = "TASK-A3a-control"

    def _build_workspace(self) -> dict:
        # Generate a 500-line PR diff
        pr_lines = []
        for i in range(100):
            pr_lines.append(f"+    def method_{i}(self):")
            pr_lines.append(f"+        return self.data[{i}]")
            pr_lines.append(f"+")
            pr_lines.append(f"     # existing code line {i}")
            pr_lines.append(f"-    old_method_{i} = None")
        pr_content = "\n".join(pr_lines)
        return {
            "files": {
                "pr_diff.patch": pr_content,
                "src/main.py": _gen_python_file("main", 100),
                "review_template.md": "# Code Review\n\n## Chunk {N}\n\n- Issues: \n- Suggestions: \n",
            },
            "tools": ["file_read", "search", "create_review", "merge_reviews"],
            "constraints": {"chunks": 5, "must_review_all_chunks": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Review this 500-line PR. Split into 5 logical chunks. "
            "Dispatch parallel review for each chunk. Merge findings "
            "into a unified review. Flag cross-chunk conflicts."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA3aControl(AdversarialTask):
    """Control for A3a: sequential review, not parallel."""
    task_id = "TASK-A3a-control"
    category = "A3-parallel-coordination"
    tier = "MEDIUM"
    title = "Code Review (Control -- Sequential)"
    target_dtypes = ["D3"]
    expected_tokens = "40K-60K"
    expected_retries = "0-1"
    stress_mechanism = "Control: sequential review eliminates parallel coordination stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return TaskA3a()._build_workspace()

    def _build_prompt(self, stress_config: dict) -> str:
        return "Review this PR sequentially, one section at a time. Produce a unified review."


class TaskA3b(AdversarialTask):
    """Parallel Test Execution and Aggregation.

    Run 6 test suites concurrently, collect results, aggregate into report.
    """
    task_id = "TASK-A3b"
    category = "A3-parallel-coordination"
    tier = "MEDIUM"
    title = "Parallel Test Execution and Aggregation"
    target_dtypes = ["D1", "D4", "D6"]
    expected_tokens = "50K-80K"
    expected_retries = "1-3"
    stress_mechanism = "If one suite times out (empty output), D1 surfaces. Late arrivals after report sealed produce D6."
    control_variant_id = "TASK-A3b-control"

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(6):
            files[f"tests/suite_{i}/test_suite.py"] = _gen_test_file(f"suite_{i}", 4)
        files["report_template.md"] = "# Test Report\n\n| Suite | Status | Failures |\n|---|---|---|\n"
        return {
            "files": files,
            "tools": ["run_tests", "file_write", "aggregate_results"],
            "constraints": {"parallel_suites": 6, "must_aggregate": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Run 6 test suites concurrently. Collect results from each suite. "
            "Aggregate into a single report with references to each suite's output."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA3bControl(AdversarialTask):
    """Control for A3b: sequential test execution."""
    task_id = "TASK-A3b-control"
    category = "A3-parallel-coordination"
    tier = "MEDIUM"
    title = "Test Execution (Control -- Sequential)"
    target_dtypes = ["D1"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: sequential execution eliminates concurrency stress."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return TaskA3b()._build_workspace()

    def _build_prompt(self, stress_config: dict) -> str:
        return "Run 6 test suites one at a time. Collect and aggregate results into a report."


# ===========================================================================
# Category A4: Error Recovery After Completion
# ===========================================================================

class TaskA4a(AdversarialTask):
    """Deploy-Then-Rollback.

    Complete deployment, mark done, then inject failure -- must reopen sealed task.
    """
    task_id = "TASK-A4a"
    category = "A4-error-recovery"
    tier = "MEDIUM"
    title = "Deploy-Then-Rollback"
    target_dtypes = ["D4", "D6", "D9"]
    expected_tokens = "50K-80K"
    expected_retries = "2-4"
    stress_mechanism = "Direct D4 (duplicate ID on re-registration), D6 (post-seal registration), and D9 (seal violation). Agent must register new artifacts in a chamber that was sealed."
    control_variant_id = "TASK-A4a-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "deploy/config.yaml": "app:\n  name: my-service\n  replicas: 3\n  image: v2.1.0\n",
                "deploy/health_check.sh": "#!/bin/bash\nexit 0\n",
                "deploy/rollback.sh": "#!/bin/bash\necho 'Rolling back to v2.0.0'\n",
                "deploy/deploy.sh": "#!/bin/bash\necho 'Deploying v2.1.0'\n",
            },
            "tools": ["deploy", "health_check", "rollback", "file_read"],
            "constraints": {"must_verify_health": True, "must_handle_rollback": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Deploy v2.1.0 of the service. Steps: "
            "1. Apply config. 2. Run deployment. 3. Verify health check. "
            "4. Mark deployment complete. "
            "THEN: Health check fails after completion. "
            "5. Diagnose failure. 6. Rollback to v2.0.0. 7. Verify rollback."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA4aControl(AdversarialTask):
    """Control for A4a: deployment without failure injection."""
    task_id = "TASK-A4a-control"
    category = "A4-error-recovery"
    tier = "MEDIUM"
    title = "Deploy-Then-Rollback (Control)"
    target_dtypes = ["D6"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: no post-completion failure, no rollback needed."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return TaskA4a()._build_workspace()

    def _build_prompt(self, stress_config: dict) -> str:
        return "Deploy v2.1.0. Apply config, deploy, verify health check, mark complete."


class TaskA4b(AdversarialTask):
    """Review-Approve-Reject Cycle.

    Code submitted, approved, sealed. Then reviewer finds problem -- must re-enter.
    """
    task_id = "TASK-A4b"
    category = "A4-error-recovery"
    tier = "MEDIUM"
    title = "Review-Approve-Reject Cycle"
    target_dtypes = ["D3", "D9"]
    expected_tokens = "50K-80K"
    expected_retries = "2-4"
    stress_mechanism = "Re-entry after approval-seal tests D9. References from rejection path to approved state test D3."
    control_variant_id = "TASK-A4b-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/feature.py": _gen_python_file("feature", 30),
                "tests/test_feature.py": _gen_test_file("feature", 5),
                "review/feedback_v1.md": "# Review v1\n\nApproved with minor comments.\n",
                "review/feedback_v2.md": "# Review v2\n\nREJECTED: Security vulnerability found in line 15.\n",
            },
            "tools": ["file_read", "file_write", "submit_review", "run_tests"],
            "constraints": {"must_pass_review": True, "must_address_rejection": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Submit code for review. It will be approved initially. "
            "Then the reviewer finds a security issue. Address the rejection, "
            "fix the vulnerability, and resubmit."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskA4bControl(AdversarialTask):
    """Control for A4b: approval without rejection."""
    task_id = "TASK-A4b-control"
    category = "A4-error-recovery"
    tier = "MEDIUM"
    title = "Review-Approve Cycle (Control)"
    target_dtypes = ["D3"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: single approval without rejection or re-entry."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        ws = TaskA4b()._build_workspace()
        del ws["files"]["review/feedback_v2.md"]
        return ws

    def _build_prompt(self, stress_config: dict) -> str:
        return "Submit code for review. Address minor comments and get approval."


# ===========================================================================
# Category B5: Ambiguous/Partial Tool Outputs
# ===========================================================================

class TaskB5a(AdversarialTask):
    """API with Intermittent Failures.

    Query API: 80% valid JSON, 10% empty, 10% malformed. Must handle all cases.
    """
    task_id = "TASK-B5a"
    category = "B5-ambiguous-partial"
    tier = "MEDIUM"
    title = "API with Intermittent Failures"
    target_dtypes = ["D1", "D5", "D8"]
    expected_tokens = "50K-80K"
    expected_retries = "3-6"
    stress_mechanism = "Empty responses should be typed as not_generated or invalid, not bare null. Tests D1, D5, D8."
    control_variant_id = "TASK-B5a-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/api_client.py": _gen_python_file("api_client", 20),
                "data/endpoints.json": json.dumps([
                    {"url": "/users", "method": "GET"},
                    {"url": "/orders", "method": "GET"},
                    {"url": "/products", "method": "GET"},
                ], indent=2),
                "tests/test_api.py": _gen_test_file("api_client", 5),
            },
            "tools": ["http_request", "file_write", "run_tests"],
            "constraints": {
                "api_reliability": 0.8,
                "empty_rate": 0.1,
                "malformed_rate": 0.1,
                "must_handle_all_cases": True,
            },
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Query 3 API endpoints and aggregate results. The API is unreliable: "
            "~80% valid JSON, ~10% empty responses, ~10% malformed JSON. "
            "Handle all failure modes gracefully. Report which endpoints succeeded "
            "and which failed with typed absence states."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB5aControl(AdversarialTask):
    """Control for B5a: always-valid API responses."""
    task_id = "TASK-B5a-control"
    category = "B5-ambiguous-partial"
    tier = "MEDIUM"
    title = "API Query (Control -- Reliable)"
    target_dtypes = ["D1"]
    expected_tokens = "30K-50K"
    expected_retries = "0-1"
    stress_mechanism = "Control: 100% reliable API, no failure handling needed."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        ws = TaskB5a()._build_workspace()
        ws["constraints"]["api_reliability"] = 1.0
        ws["constraints"]["empty_rate"] = 0.0
        ws["constraints"]["malformed_rate"] = 0.0
        return ws

    def _build_prompt(self, stress_config: dict) -> str:
        return "Query 3 API endpoints and aggregate results. The API is fully reliable."


class TaskB5b(AdversarialTask):
    """File Read with Encoding Issues.

    Mixed UTF-8 and Latin-1 encoding. Some fields decode to empty or garbage.
    """
    task_id = "TASK-B5b"
    category = "B5-ambiguous-partial"
    tier = "SHORT"
    title = "File Read with Encoding Issues"
    target_dtypes = ["D5", "D8"]
    expected_tokens = "15K-25K"
    expected_retries = "1-3"
    stress_mechanism = "Empty decoded fields test D5. Garbage content tests D8."
    control_variant_id = "TASK-B5b-control"

    def _build_workspace(self) -> dict:
        # Simulate mixed-encoding data
        data_content = (
            "name,email,notes\n"
            "Alice,alice@example.com,Regular user\n"
            "Bob,bob@example.com,Has special chars: caf\\xe9\n"
            "Charlie,,Missing email field\n"
            "Dave,dave@example.com,\n"  # Empty notes
        )
        return {
            "files": {
                "data/users.csv": data_content,
                "data/schema.json": json.dumps({
                    "required_fields": ["name", "email", "notes"],
                    "encoding": "mixed",
                }, indent=2),
            },
            "tools": ["file_read", "file_write"],
            "constraints": {"must_handle_encoding": True, "must_type_missing_fields": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Read data/users.csv (mixed encoding). Extract structured data. "
            "Handle: empty fields (type as absent), encoding errors (type as invalid), "
            "and missing values (type as not_generated)."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB5bControl(AdversarialTask):
    """Control for B5b: clean UTF-8 data."""
    task_id = "TASK-B5b-control"
    category = "B5-ambiguous-partial"
    tier = "SHORT"
    title = "File Read (Control -- Clean)"
    target_dtypes = ["D5"]
    expected_tokens = "10K-15K"
    expected_retries = "0"
    stress_mechanism = "Control: clean UTF-8 data, no encoding issues."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "data/users.csv": "name,email,notes\nAlice,alice@example.com,Regular user\n",
                "data/schema.json": json.dumps({"required_fields": ["name", "email", "notes"]}, indent=2),
            },
            "tools": ["file_read", "file_write"],
            "constraints": {},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Read data/users.csv and extract structured data."


# ===========================================================================
# Category B6: Long-Horizon Reasoning Chains
# ===========================================================================

class TaskB6a(AdversarialTask):
    """Multi-Hop Research Synthesis.

    10 documents, answer requires chaining facts across 5+. Must cite sources.
    """
    task_id = "TASK-B6a"
    category = "B6-long-horizon"
    tier = "MEDIUM"
    title = "Multi-Hop Research Synthesis"
    target_dtypes = ["D2", "D7"]
    expected_tokens = "50K-80K"
    expected_retries = "1-3"
    stress_mechanism = "Summary may lose source_refs (D2). Provenance chain is 5+ hops deep."
    control_variant_id = "TASK-B6a-control"

    def _build_workspace(self) -> dict:
        docs = {}
        for i in range(10):
            content = (
                f"# Document {i+1}\n\n"
                f"Finding: The value of parameter X_{i} is {i * 7 + 3}.\n"
                f"This depends on parameter X_{max(0, i-1)} from Document {max(1, i)}.\n"
                f"Cross-reference: see Document {min(10, i+2)} for validation.\n"
            )
            docs[f"docs/doc_{i+1:02d}.md"] = content
        docs["question.md"] = (
            "# Research Question\n\n"
            "What is the final computed value of X_9, tracing the full "
            "dependency chain from X_0 through X_9? Cite every document used."
        )
        return {
            "files": docs,
            "tools": ["file_read", "search", "file_write"],
            "constraints": {"must_cite_sources": True, "min_citations": 5},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Read 10 research documents and answer the question in question.md. "
            "Your answer must chain facts across 5+ documents and cite each "
            "source with specific document references."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB6aControl(AdversarialTask):
    """Control for B6a: answer from single document."""
    task_id = "TASK-B6a-control"
    category = "B6-long-horizon"
    tier = "SHORT"
    title = "Research Synthesis (Control -- Single Doc)"
    target_dtypes = ["D2"]
    expected_tokens = "10K-20K"
    expected_retries = "0"
    stress_mechanism = "Control: single document, no multi-hop chain."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "docs/doc_01.md": "# Document 1\n\nThe answer to the question is 42.\n",
                "question.md": "# Question\n\nWhat is the answer? Cite your source.\n",
            },
            "tools": ["file_read", "file_write"],
            "constraints": {"must_cite_sources": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Read docs/doc_01.md and answer the question. Cite the source."


class TaskB6b(AdversarialTask):
    """Iterative Data Analysis Pipeline.

    10+ sequential steps: load, clean, transform, analyze, visualize, report.
    """
    task_id = "TASK-B6b"
    category = "B6-long-horizon"
    tier = "MEDIUM"
    title = "Iterative Data Analysis Pipeline"
    target_dtypes = ["D3", "D7"]
    expected_tokens = "50K-80K"
    expected_retries = "1-3"
    stress_mechanism = "By step 10, step 1 artifacts (raw data load) may be compacted. References from report to early steps test D3 and D7."
    control_variant_id = "TASK-B6b-control"

    def _build_workspace(self) -> dict:
        # Generate synthetic CSV data
        csv_rows = ["id,timestamp,value,category\n"]
        for i in range(100):
            cat = ["A", "B", "C"][i % 3]
            csv_rows.append(f"{i},2026-03-{(i % 28) + 1:02d},{i * 1.7 + 0.3:.1f},{cat}\n")
        return {
            "files": {
                "data/raw.csv": "".join(csv_rows),
                "pipeline/config.json": json.dumps({
                    "steps": ["load", "clean", "transform", "analyze", "visualize", "report"],
                    "output_dir": "results/",
                }, indent=2),
            },
            "tools": ["file_read", "file_write", "run_analysis", "create_chart"],
            "constraints": {"must_complete_all_steps": True, "must_reference_sources": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Execute the data analysis pipeline: "
            "1. Load raw.csv 2. Clean (remove nulls) 3. Transform (normalize values) "
            "4. Group by category 5. Compute statistics 6. Create visualizations "
            "7. Generate report. Each step must reference previous step outputs."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB6bControl(AdversarialTask):
    """Control for B6b: 3-step pipeline."""
    task_id = "TASK-B6b-control"
    category = "B6-long-horizon"
    tier = "SHORT"
    title = "Data Analysis (Control -- Short Pipeline)"
    target_dtypes = ["D3"]
    expected_tokens = "15K-25K"
    expected_retries = "0"
    stress_mechanism = "Control: 3-step pipeline, no compaction-driven data loss."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        ws = TaskB6b()._build_workspace()
        ws["files"]["pipeline/config.json"] = json.dumps({
            "steps": ["load", "analyze", "report"],
        }, indent=2)
        return ws

    def _build_prompt(self, stress_config: dict) -> str:
        return "Load data, compute mean per category, write a short report."


# ===========================================================================
# Category B7: Context Window Overflow
# ===========================================================================

class TaskB7a(AdversarialTask):
    """Large Codebase Exploration.

    Navigate 50-file codebase to answer architecture question. Must read 20+ files.
    LLM compaction triggers around file 15.
    """
    task_id = "TASK-B7a"
    category = "B7-context-overflow"
    tier = "LONG"
    title = "Large Codebase Exploration"
    target_dtypes = ["D3", "D7"]
    expected_tokens = "150K-250K"
    expected_retries = "2-5"
    stress_mechanism = "Post-LLM compaction, refs to files read in the first batch may dangle (D3). Trace metadata from early reads lost (D7)."
    control_variant_id = "TASK-B7a-control"

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(50):
            module = f"module_{i:02d}"
            files[f"src/{module}.py"] = _gen_python_file(module, 25)
        files["docs/architecture.md"] = "# Architecture\n\nThe system is organized into 50 modules...\n"
        files["question.md"] = "# Question\n\nWhich module handles authentication and how does it interact with modules 10-15?\n"
        return {
            "files": files,
            "tools": ["file_read", "search", "file_write"],
            "constraints": {"must_read_at_least": 20, "must_answer_question": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Explore this 50-file codebase to answer the architecture question "
            "in question.md. You must read at least 20 files to build a complete "
            "understanding. Cite specific files in your answer."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB7aControl(AdversarialTask):
    """Control for B7a: 5-file codebase, no context overflow."""
    task_id = "TASK-B7a-control"
    category = "B7-context-overflow"
    tier = "SHORT"
    title = "Codebase Exploration (Control -- Small)"
    target_dtypes = ["D3"]
    expected_tokens = "15K-25K"
    expected_retries = "0"
    stress_mechanism = "Control: 5 files, no context overflow."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(5):
            files[f"src/module_{i}.py"] = _gen_python_file(f"module_{i}", 20)
        files["question.md"] = "# Question\n\nWhat does module_2 do?\n"
        return {
            "files": files,
            "tools": ["file_read", "search"],
            "constraints": {"must_answer_question": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Read the 5 source files and answer the question in question.md."


class TaskB7b(AdversarialTask):
    """Context Window Fill via Documentation.

    Generate extensive documentation until context window fills. Tests LLM
    compaction behavior on provenance-rich content.
    """
    task_id = "TASK-B7b"
    category = "B7-context-overflow"
    tier = "LONG"
    title = "Context Window Fill via Documentation"
    target_dtypes = ["D7", "D8"]
    expected_tokens = "150K-250K"
    expected_retries = "2-5"
    stress_mechanism = "Documentation generation fills context; LLM compaction may corrupt provenance metadata (D7) or content (D8)."
    control_variant_id = "TASK-B7b-control"

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(30):
            files[f"src/module_{i:02d}.py"] = _gen_python_file(f"module_{i:02d}", 30)
        return {
            "files": files,
            "tools": ["file_read", "file_write", "search"],
            "constraints": {"must_document_all_modules": True, "must_reference_source_files": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Generate API documentation for all 30 modules in src/. "
            "Each doc must reference the source file it documents. "
            "Include function signatures, docstrings, and cross-references "
            "between modules."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB7bControl(AdversarialTask):
    """Control for B7b: document 3 modules."""
    task_id = "TASK-B7b-control"
    category = "B7-context-overflow"
    tier = "SHORT"
    title = "Documentation Generation (Control -- Small)"
    target_dtypes = ["D7"]
    expected_tokens = "15K-25K"
    expected_retries = "0"
    stress_mechanism = "Control: 3 modules, no context overflow."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        files = {}
        for i in range(3):
            files[f"src/module_{i}.py"] = _gen_python_file(f"module_{i}", 20)
        return {
            "files": files,
            "tools": ["file_read", "file_write"],
            "constraints": {"must_document_all_modules": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Generate API documentation for all 3 modules in src/."


# ===========================================================================
# Category B8: Format/Encoding Edge Cases
# ===========================================================================

class TaskB8a(AdversarialTask):
    """Mixed Encoding File Processing.

    Process files with mixed encodings, binary data, and special characters.
    """
    task_id = "TASK-B8a"
    category = "B8-encoding-edge-cases"
    tier = "SHORT"
    title = "Mixed Encoding File Processing"
    target_dtypes = ["D5", "D8"]
    expected_tokens = "15K-25K"
    expected_retries = "1-3"
    stress_mechanism = "Mixed encodings and binary data corrupt content (D8). Missing decoded fields test D5."
    control_variant_id = "TASK-B8a-control"

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "data/utf8.txt": "Hello, world! Caf\u00e9 na\u00efve r\u00e9sum\u00e9\n",
                "data/ascii.txt": "Plain ASCII text only\n",
                "data/mixed.csv": "name,data\nAlice,\x00\x01\x02binary\n",
                "data/config.json": json.dumps({"encoding": "auto-detect"}, indent=2),
            },
            "tools": ["file_read", "file_write"],
            "constraints": {"must_handle_all_encodings": True, "must_type_failures": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        prompt = (
            "Process all files in data/. Handle encoding differences. "
            "For binary data, type the content as invalid. "
            "For decoding failures, type as not_generated."
        )
        return _add_ambiguity(prompt, stress_config["epsilon"])


class TaskB8aControl(AdversarialTask):
    """Control for B8a: clean UTF-8 only."""
    task_id = "TASK-B8a-control"
    category = "B8-encoding-edge-cases"
    tier = "SHORT"
    title = "File Processing (Control -- Clean)"
    target_dtypes = ["D5"]
    expected_tokens = "10K-15K"
    expected_retries = "0"
    stress_mechanism = "Control: clean UTF-8, no encoding issues."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "data/clean.txt": "Hello, world!\n",
                "data/config.json": json.dumps({"encoding": "utf-8"}, indent=2),
            },
            "tools": ["file_read", "file_write"],
            "constraints": {},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Read and process data/clean.txt."


# ===========================================================================
# Category C9: Control -- Simple Single-Step (Baseline)
# ===========================================================================

class TaskC9a(AdversarialTask):
    """Add License Header (same as v1.0 TASK-S1). Baseline control."""
    task_id = "TASK-C9a"
    category = "C9-control"
    tier = "SHORT"
    title = "Add License Header"
    target_dtypes = ["D1"]  # Only if LLM fails entirely
    expected_tokens = "5K-10K"
    expected_retries = "0"
    stress_mechanism = "None -- baseline control. Expected 0 violations."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/main.py": _gen_python_file("main", 15),
                "LICENSE": "MIT License\n\nCopyright (c) 2026 Test Project\n",
            },
            "tools": ["file_read", "file_write"],
            "constraints": {},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Add the MIT license header from LICENSE to the top of src/main.py."


class TaskC9b(AdversarialTask):
    """Fix One-Line Bug (same as v1.0 TASK-S2). Baseline control."""
    task_id = "TASK-C9b"
    category = "C9-control"
    tier = "SHORT"
    title = "Fix One-Line Bug"
    target_dtypes = ["D1"]
    expected_tokens = "5K-10K"
    expected_retries = "0"
    stress_mechanism = "None -- baseline control."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/calc.py": (
                    "def divide(a, b):\n"
                    "    return a / b  # Bug: no zero-division check\n"
                ),
                "tests/test_calc.py": (
                    "def test_divide_by_zero():\n"
                    "    try:\n"
                    "        divide(1, 0)\n"
                    "        assert False, 'Should raise'\n"
                    "    except ZeroDivisionError:\n"
                    "        pass\n"
                ),
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_fix_bug": True, "must_pass_tests": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Fix the bug in src/calc.py so that test_divide_by_zero passes."


class TaskC9c(AdversarialTask):
    """Write Three Unit Tests (same as v1.0 TASK-S3). Baseline control."""
    task_id = "TASK-C9c"
    category = "C9-control"
    tier = "SHORT"
    title = "Write Three Unit Tests"
    target_dtypes = ["D1"]
    expected_tokens = "5K-10K"
    expected_retries = "0"
    stress_mechanism = "None -- baseline control."
    control_variant_id = None

    def _build_workspace(self) -> dict:
        return {
            "files": {
                "src/utils.py": (
                    "def clamp(value, lo, hi):\n"
                    "    return max(lo, min(value, hi))\n\n"
                    "def capitalize_words(text):\n"
                    "    return ' '.join(w.capitalize() for w in text.split())\n\n"
                    "def flatten(nested):\n"
                    "    result = []\n"
                    "    for item in nested:\n"
                    "        if isinstance(item, list):\n"
                    "            result.extend(flatten(item))\n"
                    "        else:\n"
                    "            result.append(item)\n"
                    "    return result\n"
                ),
            },
            "tools": ["file_read", "file_write", "run_tests"],
            "constraints": {"must_write_3_tests": True, "must_pass_tests": True},
        }

    def _build_prompt(self, stress_config: dict) -> str:
        return "Write 3 unit tests for the functions in src/utils.py (clamp, capitalize_words, flatten)."


# ===========================================================================
# Corpus Registry
# ===========================================================================

# All 20 primary task templates (no control variants in primary list)
TASK_CLASSES: list[type[AdversarialTask]] = [
    TaskA1a, TaskA1b, TaskA1c,
    TaskA2a, TaskA2b, TaskA2c,
    TaskA3a, TaskA3b,
    TaskA4a, TaskA4b,
    TaskB5a, TaskB5b,
    TaskB6a, TaskB6b,
    TaskB7a, TaskB7b,
    TaskB8a,
    TaskC9a, TaskC9b, TaskC9c,
]

# Control variant classes (for Tier A and B tasks)
CONTROL_CLASSES: list[type[AdversarialTask]] = [
    TaskA1aControl, TaskA1bControl, TaskA1cControl,
    TaskA2aControl, TaskA2bControl, TaskA2cControl,
    TaskA3aControl, TaskA3bControl,
    TaskA4aControl, TaskA4bControl,
    TaskB5aControl, TaskB5bControl,
    TaskB6aControl, TaskB6bControl,
    TaskB7aControl, TaskB7bControl,
    TaskB8aControl,
]

# Combined registry: task_id -> class
ALL_TASK_CLASSES: dict[str, type[AdversarialTask]] = {}
for cls in TASK_CLASSES + CONTROL_CLASSES:
    ALL_TASK_CLASSES[cls.task_id] = cls


class AdversarialCorpus:
    """Container for the full adversarial task corpus.

    Provides iteration, lookup, manifest generation, and D-type coverage analysis.
    """

    def __init__(self):
        self._tasks: dict[str, AdversarialTask] = {}
        self._controls: dict[str, AdversarialTask] = {}
        for cls in TASK_CLASSES:
            self._tasks[cls.task_id] = cls()
        for cls in CONTROL_CLASSES:
            self._controls[cls.task_id] = cls()

    @property
    def tasks(self) -> dict[str, AdversarialTask]:
        return dict(self._tasks)

    @property
    def controls(self) -> dict[str, AdversarialTask]:
        return dict(self._controls)

    @property
    def all_tasks(self) -> dict[str, AdversarialTask]:
        return {**self._tasks, **self._controls}

    def get_task(self, task_id: str) -> AdversarialTask:
        if task_id in self._tasks:
            return self._tasks[task_id]
        if task_id in self._controls:
            return self._controls[task_id]
        raise KeyError(f"Unknown task_id: {task_id}")

    def get_dtype_coverage_matrix(self) -> dict[str, list[str]]:
        """Build D-type coverage matrix: D-type -> list of task_ids that target it."""
        matrix: dict[str, list[str]] = {f"D{i}": [] for i in range(1, 10)}
        for task in self._tasks.values():
            for dtype in task.target_dtypes:
                matrix[dtype].append(task.task_id)
        return matrix

    def get_category_coverage(self) -> dict[str, list[str]]:
        """Map category -> list of task_ids."""
        coverage: dict[str, list[str]] = {}
        for task in self._tasks.values():
            cat = task.category.split("-")[0]  # e.g., "A1" from "A1-multistep-chains"
            coverage.setdefault(cat, []).append(task.task_id)
        return coverage

    def get_dtype_category_coverage(self) -> dict[str, set[str]]:
        """D-type -> set of distinct categories targeting it (not just task_ids)."""
        coverage: dict[str, set[str]] = {f"D{i}": set() for i in range(1, 10)}
        for task in self._tasks.values():
            cat = task.category.split("-")[0]
            for dtype in task.target_dtypes:
                coverage[dtype].add(cat)
        return coverage

    def get_tier_distribution(self) -> dict[str, int]:
        """Count tasks per tier."""
        dist: dict[str, int] = {"SHORT": 0, "MEDIUM": 0, "LONG": 0, "EXTREME": 0}
        for task in self._tasks.values():
            dist[task.tier] += 1
        return dist

    # --- Runs per task (per RESEARCH Section 5.1) ---

    RUNS_PER_TASK: dict[str, int] = {
        "TASK-A1a": 12, "TASK-A1b": 12, "TASK-A1c": 12,
        "TASK-A2a": 12, "TASK-A2b": 12, "TASK-A2c": 12,
        "TASK-A3a": 10, "TASK-A3b": 10,
        "TASK-A4a": 10, "TASK-A4b": 10,
        "TASK-B5a": 10, "TASK-B5b": 10,
        "TASK-B6a": 10, "TASK-B6b": 10,
        "TASK-B7a": 10, "TASK-B7b": 10,
        "TASK-B8a": 8,
        "TASK-C9a": 7, "TASK-C9b": 7, "TASK-C9c": 7,
    }

    def get_total_planned_runs(self) -> int:
        return sum(self.RUNS_PER_TASK.get(tid, 0) for tid in self._tasks)

    def generate_manifest(self) -> dict:
        """Generate the full corpus manifest as a dict."""
        dtype_matrix = self.get_dtype_coverage_matrix()
        category_coverage = self.get_category_coverage()
        tier_dist = self.get_tier_distribution()
        tasks_list = []
        for task in self._tasks.values():
            runs = self.RUNS_PER_TASK.get(task.task_id, 0)
            meta = task.get_metadata()
            meta["runs_planned"] = runs
            meta["stress_levels"] = list(STRESS_LEVELS.keys())
            tasks_list.append(meta)

        return {
            "version": "7.0",
            "total_tasks": len(self._tasks),
            "total_planned_runs": self.get_total_planned_runs(),
            "tier_distribution": tier_dist,
            "categories": category_coverage,
            "tasks": tasks_list,
            "dtype_coverage_matrix": {
                k: v for k, v in dtype_matrix.items()
            },
            "stress_levels": STRESS_LEVELS,
        }

    def write_manifest(self, path: str | Path = "data/campaign/corpus_manifest.json"):
        """Write corpus manifest to JSON file."""
        manifest = self.generate_manifest()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2, default=list)
        return manifest
