"""
test_forge_ontology.py -- Property-based and mutation-targeted tests for the
absence state ontology.

Tests the transition table formalized in Plan 01 via:
1. Hypothesis RuleBasedStateMachine (positive: legal transitions maintain invariants)
2. Parametrized negative tests (every illegal transition is correctly rejected)
3. Structural invariant tests (completeness, terminal, initial, self-transitions)

Plan: 01-02 (Property-Based Testing and Mutation Testing)
Phase: 01-ontology-formalization-and-verification
"""

from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)
from hypothesis import settings, given, strategies as st
import pytest

from forge_nulls import (
    V1_ABSENCE_STATES,
    AbsenceState,
    validate_transition,
    TRANSITION_TABLE,
)
