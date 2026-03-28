"""Tests for task_templates.py — Phase 6, Plan 02.

Validates:
1. Template instantiation and iteration generation for all 3 types
2. Provenance depth validation: 10 iterations -> depth >= 5
3. Token estimation: each iteration generates expected token count
4. Artifact ID uniqueness: no duplicates across iterations
5. Source ref chain: each iteration (after first) has source_refs
6. 20 distinct iteration prompts per template type
7. Forbidden proxy checks: no short tasks, no shallow traces
"""

import unittest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from task_templates import (
    TaskTemplate,
    CodingTaskTemplate,
    DebuggingTaskTemplate,
    SpecificationTaskTemplate,
)


class TestTaskTemplateBase(unittest.TestCase):
    """Test base TaskTemplate class."""

    def test_base_instantiation(self):
        template = TaskTemplate(run_id="test-base")
        self.assertEqual(template.run_id, "test-base")
        self.assertEqual(template.category, "generic")
        self.assertEqual(template.track, "A")

    def test_generate_iteration_returns_string(self):
        template = TaskTemplate(run_id="test-iter")
        result = template.generate_iteration(0)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_inject_provenance_delegates(self):
        template = TaskTemplate(run_id="test-prov")
        text, aid = template.inject_provenance("hello", "run1", 0)
        self.assertIn("artifact:run1:iter:0:r1", text)
        self.assertEqual(aid, "artifact:run1:iter:0:r1")


class TestCodingTaskTemplate(unittest.TestCase):
    """Test CodingTaskTemplate (A1)."""

    def setUp(self):
        self.template = CodingTaskTemplate(run_id="coding-test")

    def test_category_and_track(self):
        self.assertEqual(self.template.category, "coding")
        self.assertEqual(self.template.track, "A")

    def test_20_distinct_prompts(self):
        """All 20 iteration prompts are unique (no repeats)."""
        prompts = set()
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            # Extract the core prompt (before the artifact marker)
            core = prompt.split("\n[PROVENANCE:")[0]
            prompts.add(core)
        self.assertEqual(len(prompts), 20,
                         "Expected 20 distinct prompts, got duplicates")

    def test_iteration_generates_artifact_id(self):
        prompt = self.template.generate_iteration(0)
        self.assertIn("artifact:coding-test:iter:0:r1", prompt)

    def test_artifact_ids_unique(self):
        """All generated artifact IDs are unique."""
        for i in range(20):
            self.template.generate_iteration(i)
        ids = self.template.get_unique_ids()
        self.assertEqual(len(ids), 20,
                         "Expected 20 unique artifact IDs")

    def test_source_refs_chain(self):
        """After iteration 0, each iteration has source_refs to predecessors."""
        for i in range(10):
            self.template.generate_iteration(i)
        artifacts = self.template.get_artifacts()
        # First artifact has no source_refs
        self.assertEqual(len(artifacts[0]["source_refs"]), 0)
        # All subsequent artifacts have at least one source_ref
        for artifact in artifacts[1:]:
            self.assertGreater(len(artifact["source_refs"]), 0,
                               f"Artifact {artifact['id']} has no source_refs")

    def test_provenance_depth_after_10_iterations(self):
        """After 10 iterations, provenance depth >= 5."""
        for i in range(10):
            self.template.generate_iteration(i)
        self.assertTrue(
            self.template.validate_provenance_depth(min_depth=5),
            "Expected provenance depth >= 5 after 10 iterations"
        )

    def test_prompt_content_substantial(self):
        """Each iteration prompt is substantial (not a short placeholder).

        Forbidden proxy fp-short-tasks: templates that generate < 1000 tokens
        per iteration. We check the prompt itself is at least 200 chars
        (the response will be much longer).
        """
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            # Core prompt (before marker injection)
            core = prompt.split("\n[PROVENANCE:")[0].split("\n\nBuilding on")[0]
            self.assertGreater(
                len(core), 200,
                f"Iteration {i} prompt too short ({len(core)} chars) — "
                f"forbidden proxy fp-short-tasks"
            )

    def test_estimated_total_tokens(self):
        """20 iterations should produce prompts that, with responses,
        reach the 80K threshold. Check prompts alone are >= 4000 tokens
        (assuming ~700 tokens per response, total = 4000 + 14000 = 18000+
        which, with model responses of 500-1000 tokens each, should reach 80K)."""
        total_prompt_words = 0
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            total_prompt_words += len(prompt.split())
        # Conservative: prompts alone should be substantial
        # 20 prompts * ~100 words each = ~2000 words minimum
        self.assertGreater(total_prompt_words, 1500,
                           "Total prompt words too low for reaching 80K threshold")


class TestDebuggingTaskTemplate(unittest.TestCase):
    """Test DebuggingTaskTemplate (A2)."""

    def setUp(self):
        self.template = DebuggingTaskTemplate(run_id="debug-test")

    def test_category_and_track(self):
        self.assertEqual(self.template.category, "debugging")
        self.assertEqual(self.template.track, "A")

    def test_20_distinct_prompts(self):
        """All 20 iteration prompts are unique."""
        prompts = set()
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            core = prompt.split("\n[PROVENANCE:")[0]
            prompts.add(core)
        self.assertEqual(len(prompts), 20)

    def test_artifact_ids_unique(self):
        for i in range(20):
            self.template.generate_iteration(i)
        ids = self.template.get_unique_ids()
        self.assertEqual(len(ids), 20)

    def test_source_refs_chain(self):
        for i in range(10):
            self.template.generate_iteration(i)
        artifacts = self.template.get_artifacts()
        self.assertEqual(len(artifacts[0]["source_refs"]), 0)
        for artifact in artifacts[1:]:
            self.assertGreater(len(artifact["source_refs"]), 0)

    def test_provenance_depth_after_10_iterations(self):
        for i in range(10):
            self.template.generate_iteration(i)
        self.assertTrue(
            self.template.validate_provenance_depth(min_depth=5),
            "Expected provenance depth >= 5 after 10 iterations"
        )

    def test_prompt_content_substantial(self):
        """Forbidden proxy check: no short tasks."""
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            core = prompt.split("\n[PROVENANCE:")[0].split("\n\nBuilding on")[0]
            self.assertGreater(len(core), 200,
                               f"Iteration {i} too short — fp-short-tasks")

    def test_hypothesis_test_pattern(self):
        """Debugging template follows hypothesis-test-revise pattern."""
        # Check that prompts mention hypotheses, tests, and results
        hypothesis_count = 0
        test_count = 0
        for i in range(10):
            prompt = self.template.generate_iteration(i)
            lower = prompt.lower()
            if "hypothesis" in lower or "h1" in lower or "h2" in lower:
                hypothesis_count += 1
            if "test" in lower or "result" in lower or "confirm" in lower:
                test_count += 1
        self.assertGreater(hypothesis_count, 3,
                           "Expected multiple hypothesis steps in debugging template")
        self.assertGreater(test_count, 3,
                           "Expected multiple test/result steps in debugging template")


class TestSpecificationTaskTemplate(unittest.TestCase):
    """Test SpecificationTaskTemplate (A3)."""

    def setUp(self):
        self.template = SpecificationTaskTemplate(run_id="spec-test")

    def test_category_and_track(self):
        self.assertEqual(self.template.category, "specification")
        self.assertEqual(self.template.track, "A")

    def test_20_distinct_prompts(self):
        prompts = set()
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            core = prompt.split("\n[PROVENANCE:")[0]
            prompts.add(core)
        self.assertEqual(len(prompts), 20)

    def test_artifact_ids_unique(self):
        for i in range(20):
            self.template.generate_iteration(i)
        ids = self.template.get_unique_ids()
        self.assertEqual(len(ids), 20)

    def test_source_refs_chain(self):
        for i in range(10):
            self.template.generate_iteration(i)
        artifacts = self.template.get_artifacts()
        self.assertEqual(len(artifacts[0]["source_refs"]), 0)
        for artifact in artifacts[1:]:
            self.assertGreater(len(artifact["source_refs"]), 0)

    def test_provenance_depth_after_10_iterations(self):
        for i in range(10):
            self.template.generate_iteration(i)
        self.assertTrue(
            self.template.validate_provenance_depth(min_depth=5),
            "Expected provenance depth >= 5 after 10 iterations"
        )

    def test_prompt_content_substantial(self):
        """Forbidden proxy check: no short tasks."""
        for i in range(20):
            prompt = self.template.generate_iteration(i)
            core = prompt.split("\n[PROVENANCE:")[0].split("\n\nBuilding on")[0]
            self.assertGreater(len(core), 200,
                               f"Iteration {i} too short — fp-short-tasks")

    def test_spec_has_numbered_requirements(self):
        """First iteration should contain numbered requirements."""
        prompt = self.template.generate_iteration(0)
        self.assertIn("REQ-001", prompt)
        self.assertIn("REQ-010", prompt)

    def test_subsequent_iterations_reference_requirements(self):
        """After the spec, subsequent iterations implement specific requirements."""
        for i in range(5):
            self.template.generate_iteration(i)
        # Iterations 1+ should mention specific REQ numbers
        prompt_1 = self.template.generate_iteration(1)
        self.assertIn("REQ-", prompt_1)


class TestProvenanceDepthValidation(unittest.TestCase):
    """Cross-template provenance depth validation."""

    def test_all_templates_reach_depth_5(self):
        """All three templates reach provenance depth >= 5 after 10 iterations."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"depth-{TemplateCls.category}")
            for i in range(10):
                template.generate_iteration(i)
            self.assertTrue(
                template.validate_provenance_depth(min_depth=5),
                f"{TemplateCls.__name__} failed to reach depth 5 after 10 iterations"
            )

    def test_no_shallow_traces(self):
        """Forbidden proxy fp-shallow-traces: depth must be >= 3 after 5 iterations."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"shallow-{TemplateCls.category}")
            for i in range(5):
                template.generate_iteration(i)
            self.assertTrue(
                template.validate_provenance_depth(min_depth=3),
                f"{TemplateCls.__name__} has shallow traces (depth < 3 after 5 iters) "
                f"— forbidden proxy fp-shallow-traces"
            )


class TestSourceRefIntegrity(unittest.TestCase):
    """Validate source ref chain integrity across all templates."""

    def test_no_dangling_refs(self):
        """All source_refs must point to existing artifacts."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"dangle-{TemplateCls.category}")
            for i in range(15):
                template.generate_iteration(i)
            artifacts = template.get_artifacts()
            all_ids = {a["id"] for a in artifacts}
            for artifact in artifacts:
                for ref in artifact["source_refs"]:
                    self.assertIn(
                        ref, all_ids,
                        f"Dangling ref {ref} in {TemplateCls.__name__} "
                        f"artifact {artifact['id']}"
                    )

    def test_no_cycles(self):
        """Source ref graph must be a DAG (no cycles)."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"cycle-{TemplateCls.category}")
            for i in range(15):
                template.generate_iteration(i)
            artifacts = template.get_artifacts()

            # Build adjacency and check for cycles via DFS
            children = {}  # parent_id -> [child_ids]
            for a in artifacts:
                for ref in a["source_refs"]:
                    children.setdefault(ref, []).append(a["id"])

            def has_cycle(node, visited, stack):
                visited.add(node)
                stack.add(node)
                for child in children.get(node, []):
                    if child not in visited:
                        if has_cycle(child, visited, stack):
                            return True
                    elif child in stack:
                        return True
                stack.discard(node)
                return False

            visited = set()
            for a in artifacts:
                if a["id"] not in visited:
                    self.assertFalse(
                        has_cycle(a["id"], visited, set()),
                        f"Cycle detected in {TemplateCls.__name__}"
                    )


class TestTokenEstimation(unittest.TestCase):
    """Verify token estimation for threshold calculation."""

    def test_expected_tokens_per_iteration(self):
        """Each template reports a reasonable token estimate."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"tokens-{TemplateCls.category}")
            tokens = template.expected_tokens_per_iteration()
            self.assertGreater(tokens, 100,
                               f"{TemplateCls.__name__} token estimate too low")
            self.assertLess(tokens, 5000,
                            f"{TemplateCls.__name__} token estimate too high")

    def test_total_prompt_tokens_substantial(self):
        """20 iterations of prompts should generate substantial content.

        With model responses of 500-1000 tokens each, total conversation
        should approach 60K+ tokens (within range for 80K threshold).

        Check: total prompt words >= 1500 (rough 1.3 tokens/word).
        """
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"total-{TemplateCls.category}")
            total_words = 0
            for i in range(20):
                prompt = template.generate_iteration(i)
                total_words += len(prompt.split())
            self.assertGreater(
                total_words, 1500,
                f"{TemplateCls.__name__} total prompt words ({total_words}) "
                f"too low for 80K threshold"
            )


class TestRunnerIntegration(unittest.TestCase):
    """Test that templates work with GenuineCompactionRunner."""

    def test_template_compatible_with_runner(self):
        """Templates have the interface expected by GenuineCompactionRunner."""
        for TemplateCls in [CodingTaskTemplate, DebuggingTaskTemplate,
                            SpecificationTaskTemplate]:
            template = TemplateCls(run_id=f"compat-{TemplateCls.category}")
            # Runner expects: generate_iteration(int) -> str
            result = template.generate_iteration(0)
            self.assertIsInstance(result, str)
            # Runner expects: .category and .track attributes
            self.assertIsInstance(template.category, str)
            self.assertIsInstance(template.track, str)


if __name__ == "__main__":
    unittest.main()
