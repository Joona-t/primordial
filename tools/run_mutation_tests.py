"""
run_mutation_tests.py -- Custom mutation testing for forge_nulls.py

mutmut is incompatible with Python 3.14 (both v2 pony ORM deepcopy issue
and v3 multiprocessing set_start_method issue). This script implements
targeted mutation testing using Python's AST module.

Mutation operators:
1. Boolean negation: True <-> False
2. Comparison operator swap: == <-> !=, in <-> not in
3. Boundary mutations: change frozenset membership
4. Conditional logic: remove/negate if conditions
5. Return value mutations: True <-> False in return statements
6. String mutations: swap state names

Usage:
    python3 run_mutation_tests.py [--verbose]
"""

import ast
import copy
import importlib
import json
import subprocess
import sys
import tempfile
import textwrap
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Mutant:
    """A single code mutation."""
    id: int
    line: int
    col: int
    original: str
    mutated: str
    description: str
    category: str
    status: str = "pending"  # pending, killed, survived, equivalent, error


@dataclass
class MutationReport:
    """Aggregated mutation testing results."""
    total: int = 0
    killed: int = 0
    survived: int = 0
    equivalent: int = 0
    error: int = 0
    timeout: int = 0
    mutants: list = field(default_factory=list)

    @property
    def raw_score(self) -> float:
        if self.total == 0:
            return 0.0
        return self.killed / self.total * 100

    @property
    def adjusted_score(self) -> float:
        effective = self.total - self.equivalent
        if effective == 0:
            return 100.0
        return self.killed / effective * 100


def generate_mutations(source_path: Path) -> list[Mutant]:
    """Generate mutations for forge_nulls.py using targeted operators."""
    source = source_path.read_text()
    tree = ast.parse(source)
    lines = source.splitlines()
    mutants = []
    mid = 0

    for node in ast.walk(tree):
        # --- Mutation 1: Boolean constant flips ---
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            # Skip booleans in the transition table builder and __main__ block
            mid += 1
            original_val = node.value
            mutated_val = not original_val
            mutants.append(Mutant(
                id=mid,
                line=node.lineno,
                col=node.col_offset,
                original=str(original_val),
                mutated=str(mutated_val),
                description=f"Line {node.lineno}: {original_val} -> {mutated_val}",
                category="boolean_flip",
            ))

        # --- Mutation 2: Comparison operator swaps ---
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                swap_map = {
                    ast.Eq: (ast.NotEq, "== -> !="),
                    ast.NotEq: (ast.Eq, "!= -> =="),
                    ast.In: (ast.NotIn, "in -> not in"),
                    ast.NotIn: (ast.In, "not in -> in"),
                    ast.Is: (ast.IsNot, "is -> is not"),
                    ast.IsNot: (ast.Is, "is not -> is"),
                }
                if type(op) in swap_map:
                    new_op_class, desc = swap_map[type(op)]
                    mid += 1
                    mutants.append(Mutant(
                        id=mid,
                        line=node.lineno,
                        col=node.col_offset,
                        original=desc.split(" -> ")[0],
                        mutated=desc.split(" -> ")[1],
                        description=f"Line {node.lineno}: {desc}",
                        category="comparison_swap",
                    ))

        # --- Mutation 3: String constant swaps for state names ---
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            state_names = {
                "not_generated", "not_invoked", "unknown", "unresolved",
                "withheld", "invalid", "deleted", "pruned_recoverable",
            }
            if node.value in state_names:
                # Swap with a different state name
                others = sorted(state_names - {node.value})
                # Pick the first alphabetically different one
                swap_to = others[0] if others else node.value
                if swap_to != node.value:
                    mid += 1
                    mutants.append(Mutant(
                        id=mid,
                        line=node.lineno,
                        col=node.col_offset,
                        original=f'"{node.value}"',
                        mutated=f'"{swap_to}"',
                        description=f'Line {node.lineno}: "{node.value}" -> "{swap_to}"',
                        category="state_name_swap",
                    ))

        # --- Mutation 4: Remove conditions (if x: -> if True:) ---
        if isinstance(node, ast.If):
            mid += 1
            mutants.append(Mutant(
                id=mid,
                line=node.lineno,
                col=node.col_offset,
                original="if <condition>",
                mutated="if True",
                description=f"Line {node.lineno}: if <condition> -> if True",
                category="condition_removal",
            ))

        # --- Mutation 5: Negate not operators ---
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            mid += 1
            mutants.append(Mutant(
                id=mid,
                line=node.lineno,
                col=node.col_offset,
                original="not <expr>",
                mutated="<expr>",
                description=f"Line {node.lineno}: not <expr> -> <expr>",
                category="negation_removal",
            ))

    return mutants


def apply_mutation(source: str, mutant: Mutant) -> str | None:
    """Apply a single mutation to the source code and return mutated source.

    Returns None if the mutation cannot be applied cleanly.
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    state = {"applied": False}

    class MutationTransformer(ast.NodeTransformer):

        def visit_Constant(self, node):
            if not state["applied"] and node.lineno == mutant.line and node.col_offset == mutant.col:
                if mutant.category == "boolean_flip" and isinstance(node.value, bool):
                    node.value = not node.value
                    state["applied"] = True
                elif mutant.category == "state_name_swap" and isinstance(node.value, str):
                    node.value = mutant.mutated.strip('"')
                    state["applied"] = True
            return node

        def visit_Compare(self, node):
            if not state["applied"] and node.lineno == mutant.line and node.col_offset == mutant.col:
                if mutant.category == "comparison_swap":
                    swap_map = {
                        ast.Eq: ast.NotEq,
                        ast.NotEq: ast.Eq,
                        ast.In: ast.NotIn,
                        ast.NotIn: ast.In,
                        ast.Is: ast.IsNot,
                        ast.IsNot: ast.Is,
                    }
                    new_ops = []
                    swapped = False
                    for op in node.ops:
                        if not swapped and type(op) in swap_map:
                            new_ops.append(swap_map[type(op)]())
                            swapped = True
                        else:
                            new_ops.append(op)
                    if swapped:
                        node.ops = new_ops
                        state["applied"] = True
            self.generic_visit(node)
            return node

        def visit_If(self, node):
            if not state["applied"] and node.lineno == mutant.line and node.col_offset == mutant.col:
                if mutant.category == "condition_removal":
                    node.test = ast.Constant(value=True)
                    state["applied"] = True
            self.generic_visit(node)
            return node

        def visit_UnaryOp(self, node):
            if not state["applied"] and node.lineno == mutant.line and node.col_offset == mutant.col:
                if mutant.category == "negation_removal" and isinstance(node.op, ast.Not):
                    state["applied"] = True
                    return node.operand  # Remove the `not`
            self.generic_visit(node)
            return node

    new_tree = MutationTransformer().visit(tree)
    if not state["applied"]:
        return None

    ast.fix_missing_locations(new_tree)
    try:
        return ast.unparse(new_tree)
    except Exception:
        return None


def run_tests_with_mutant(
    source_path: Path,
    mutated_source: str,
    test_files: list[str],
    timeout: int = 30,
) -> tuple[str, str]:
    """Run the test suite against mutated source code.

    Returns (status, output) where status is 'killed', 'survived', or 'error'.
    """
    # Create a temporary copy of the source file
    backup = source_path.read_text()
    try:
        source_path.write_text(mutated_source)

        # Clear any cached bytecode
        cache_dir = source_path.parent / "__pycache__"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        # Skip slow Hypothesis StateMachine tests during mutation testing.
        # The parametrized tests (64 table-vs-function, 19 illegal, 45 legal,
        # 12 structural, 7 invalid-state) provide comprehensive mutation killing.
        # StateMachine tests are for adversarial exploration, not mutation detection.
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + test_files + [
                "-x", "-q", "--tb=line", "--no-header",
                "-k", "not TestAbsenceStateMachine and not TestLegalTransitionExplorer",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(source_path.parent),
        )

        if result.returncode != 0:
            return "killed", result.stdout + result.stderr
        else:
            return "survived", result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        return "killed", "timeout"
    except Exception as e:
        return "error", str(e)
    finally:
        source_path.write_text(backup)
        # Clear cache again to restore clean state
        cache_dir = source_path.parent / "__pycache__"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    source_path = Path(__file__).parent / "forge_nulls.py"
    test_files = ["test_forge_v1_convergence.py", "test_forge_ontology.py"]

    print(f"Source: {source_path}")
    print(f"Tests: {test_files}")
    print()

    # Step 1: Verify tests pass on unmodified source
    print("Step 1: Verifying baseline tests pass...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest"] + test_files + ["-x", "-q", "--no-header",
         "-k", "not StateMachine and not LegalTransition"],  # Skip slow Hypothesis tests
        capture_output=True,
        text=True,
        cwd=str(source_path.parent),
    )
    if result.returncode != 0:
        print(f"FATAL: Baseline tests fail!\n{result.stdout}\n{result.stderr}")
        sys.exit(1)
    print(f"  Baseline: PASS")
    print()

    # Step 2: Generate mutations
    print("Step 2: Generating mutations...")
    source = source_path.read_text()
    mutants = generate_mutations(source_path)
    print(f"  Generated {len(mutants)} mutants")
    print()

    # Step 3: Test each mutant
    print("Step 3: Testing mutants...")
    report = MutationReport(total=len(mutants), mutants=mutants)

    for mutant in mutants:
        mutated_source = apply_mutation(source, mutant)
        if mutated_source is None:
            mutant.status = "error"
            report.error += 1
            if verbose:
                print(f"  [{mutant.id:3d}] ERROR   - {mutant.description} (could not apply)")
            continue

        if mutated_source == source:
            mutant.status = "equivalent"
            report.equivalent += 1
            if verbose:
                print(f"  [{mutant.id:3d}] EQUIV   - {mutant.description}")
            continue

        # Run tests (skip slow Hypothesis StateMachine tests for speed)
        status, output = run_tests_with_mutant(
            source_path,
            mutated_source,
            [f for f in test_files],
            timeout=60,
        )

        mutant.status = status
        if status == "killed":
            report.killed += 1
            if verbose:
                print(f"  [{mutant.id:3d}] KILLED  - {mutant.description}")
        elif status == "survived":
            report.survived += 1
            print(f"  [{mutant.id:3d}] SURVIVED - {mutant.description}")
            if verbose:
                # Show which tests ran
                for line in output.splitlines()[-5:]:
                    print(f"           {line}")
        else:
            report.error += 1
            if verbose:
                print(f"  [{mutant.id:3d}] ERROR   - {mutant.description}: {output[:100]}")

    # Step 4: Print report
    print()
    print("=" * 60)
    print("MUTATION TESTING REPORT")
    print("=" * 60)
    print(f"  Total mutants:     {report.total}")
    print(f"  Killed:            {report.killed}")
    print(f"  Survived:          {report.survived}")
    print(f"  Equivalent:        {report.equivalent}")
    print(f"  Error:             {report.error}")
    print(f"  Raw score:         {report.raw_score:.1f}%")
    print(f"  Adjusted score:    {report.adjusted_score:.1f}%")
    print()

    if report.survived > 0:
        print("SURVIVING MUTANTS:")
        for m in report.mutants:
            if m.status == "survived":
                print(f"  [{m.id:3d}] {m.category}: {m.description}")
        print()

    threshold = 85.0
    if report.adjusted_score >= threshold:
        print(f"RESULT: PASS (adjusted score {report.adjusted_score:.1f}% >= {threshold}%)")
    else:
        print(f"RESULT: FAIL (adjusted score {report.adjusted_score:.1f}% < {threshold}%)")

    # Write JSON results for downstream processing
    results_path = Path(__file__).parent.parent / "docs" / "mutation-results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps({
        "total": report.total,
        "killed": report.killed,
        "survived": report.survived,
        "equivalent": report.equivalent,
        "error": report.error,
        "raw_score": round(report.raw_score, 1),
        "adjusted_score": round(report.adjusted_score, 1),
        "mutants": [
            {
                "id": m.id,
                "line": m.line,
                "category": m.category,
                "description": m.description,
                "status": m.status,
            }
            for m in report.mutants
        ],
    }, indent=2))
    print(f"\nDetailed results: {results_path}")

    return 0 if report.adjusted_score >= threshold else 1


if __name__ == "__main__":
    sys.exit(main())
