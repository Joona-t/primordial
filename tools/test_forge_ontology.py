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
    _INITIAL_STATES,
    _TERMINAL_STATES,
)


# ---------------------------------------------------------------------------
# Derived test data from the transition table
# ---------------------------------------------------------------------------

SORTED_STATES = sorted(V1_ABSENCE_STATES)

# All (from, to) pairs where validate_transition returns False
ILLEGAL_TRANSITIONS = [
    (src, tgt)
    for src in SORTED_STATES
    for tgt in SORTED_STATES
    if not TRANSITION_TABLE[(src, tgt)]
]

# All (from, to) pairs where validate_transition returns True
LEGAL_TRANSITIONS = [
    (src, tgt)
    for src in SORTED_STATES
    for tgt in SORTED_STATES
    if TRANSITION_TABLE[(src, tgt)]
]


# ---------------------------------------------------------------------------
# CATEGORY A: Hypothesis RuleBasedStateMachine (positive testing)
# ---------------------------------------------------------------------------


class AbsenceStateMachine(RuleBasedStateMachine):
    """Models an entity whose absence state evolves through transitions.

    Hypothesis generates 10K+ random sequences of 30 steps each,
    exploring the reachable state space adversarially. Invariants are
    checked after every step.
    """

    def __init__(self):
        super().__init__()
        self.state = None  # Set by @initialize
        self.transition_log = []
        self.states_visited = set()

    @initialize()
    def init_state(self):
        """Start in a random valid absence state."""
        import random
        self.state = random.choice(SORTED_STATES)
        self.states_visited.add(self.state)

    @rule(target_state=st.sampled_from(SORTED_STATES))
    def attempt_transition(self, target_state):
        """Attempt a transition and verify it agrees with validate_transition().

        Both legal and illegal transitions are attempted. Legal ones
        update the state; illegal ones are verified to be rejected.
        """
        is_legal = validate_transition(self.state, target_state)

        # Cross-check: validate_transition must agree with TRANSITION_TABLE
        assert is_legal == TRANSITION_TABLE[(self.state, target_state)], (
            f"validate_transition({self.state!r}, {target_state!r}) = {is_legal} "
            f"but TRANSITION_TABLE says {TRANSITION_TABLE[(self.state, target_state)]}"
        )

        if is_legal:
            self.transition_log.append((self.state, target_state))
            self.state = target_state
            self.states_visited.add(target_state)

    @invariant()
    def state_is_valid(self):
        """Current state is always in V1_ABSENCE_STATES."""
        assert self.state in V1_ABSENCE_STATES, (
            f"Current state {self.state!r} is not a valid absence state"
        )

    @invariant()
    def no_illegal_transition_accepted(self):
        """No illegal transition was accepted into the log."""
        for from_s, to_s in self.transition_log:
            assert validate_transition(from_s, to_s), (
                f"Logged transition {from_s} -> {to_s} but "
                f"validate_transition returns False"
            )

    @invariant()
    def terminal_state_respected(self):
        """If in 'deleted', no outgoing transitions except self are legal."""
        if self.state == "deleted":
            for s in SORTED_STATES:
                if s != "deleted":
                    assert not validate_transition("deleted", s), (
                        f"deleted -> {s} should be illegal (terminal state)"
                    )

    @invariant()
    def initial_states_unreachable_from_others(self):
        """Cannot transition INTO not_invoked or not_generated from a different state."""
        for from_s, to_s in self.transition_log:
            if to_s in _INITIAL_STATES and from_s != to_s:
                raise AssertionError(
                    f"Reached initial state {to_s!r} from {from_s!r} -- "
                    f"initial states have no incoming transitions"
                )

    @invariant()
    def transition_log_consistency(self):
        """Each transition in the log must chain: log[i].to == log[i+1].from."""
        for i in range(len(self.transition_log) - 1):
            _, to_s = self.transition_log[i]
            from_next, _ = self.transition_log[i + 1]
            assert to_s == from_next, (
                f"Transition log broken at index {i}: "
                f"step {i} ends at {to_s!r} but step {i+1} starts at {from_next!r}"
            )


# Run with 10K examples, 30 steps each = ~300K transition attempts
TestAbsenceStateMachine = AbsenceStateMachine.TestCase
TestAbsenceStateMachine.settings = settings(
    max_examples=10000,
    stateful_step_count=30,
    deadline=None,  # No per-example time limit
)


class LegalTransitionExplorer(RuleBasedStateMachine):
    """Only takes legal transitions, verifying post-conditions.

    This explores the reachable state space more efficiently by filtering
    to only legal moves. It verifies that reachable states from non-terminal
    starting points include all active states.
    """

    def __init__(self):
        super().__init__()
        self.state = None
        self.transitions_taken = 0
        self.states_reached = set()

    @initialize()
    def init_state(self):
        import random
        self.state = random.choice(SORTED_STATES)
        self.states_reached.add(self.state)

    @rule(target_state=st.sampled_from(SORTED_STATES))
    def take_legal_transition(self, target_state):
        """Only take transitions that are legal."""
        if validate_transition(self.state, target_state):
            self.state = target_state
            self.transitions_taken += 1
            self.states_reached.add(target_state)

    @invariant()
    def state_always_valid(self):
        """The current state is always valid."""
        assert self.state in V1_ABSENCE_STATES

    @invariant()
    def deleted_is_absorbing(self):
        """Once in 'deleted', only self-transition is possible."""
        if self.state == "deleted":
            reachable = [
                s for s in SORTED_STATES
                if s != "deleted" and validate_transition("deleted", s)
            ]
            assert reachable == [], (
                f"deleted should be absorbing but can reach: {reachable}"
            )


TestLegalTransitionExplorer = LegalTransitionExplorer.TestCase
TestLegalTransitionExplorer.settings = settings(
    max_examples=5000,
    stateful_step_count=50,
    deadline=None,
)


# ---------------------------------------------------------------------------
# CATEGORY B: Parametrized negative tests (illegal transitions)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("from_state,to_state", ILLEGAL_TRANSITIONS)
def test_illegal_transition_rejected(from_state, to_state):
    """Every illegal transition must be rejected by validate_transition()."""
    result = validate_transition(from_state, to_state)
    assert result is False, (
        f"Expected illegal: {from_state} -> {to_state}, "
        f"but validate_transition returned {result}"
    )


@pytest.mark.parametrize("from_state,to_state", LEGAL_TRANSITIONS)
def test_legal_transition_accepted(from_state, to_state):
    """Every legal transition must be accepted by validate_transition()."""
    result = validate_transition(from_state, to_state)
    assert result is True, (
        f"Expected legal: {from_state} -> {to_state}, "
        f"but validate_transition returned {result}"
    )


# ---------------------------------------------------------------------------
# CATEGORY C: Structural invariant tests
# ---------------------------------------------------------------------------


class TestTransitionTableStructure:
    """Structural invariants of the 8-state transition table."""

    def test_transition_table_completeness(self):
        """Every (source, target) pair in the 8-state product is classified."""
        classified = 0
        for from_s in SORTED_STATES:
            for to_s in SORTED_STATES:
                result = validate_transition(from_s, to_s)
                assert isinstance(result, bool), (
                    f"validate_transition({from_s!r}, {to_s!r}) returned "
                    f"{type(result).__name__}, not bool"
                )
                classified += 1
        assert classified == 64, f"Expected 64 entries, got {classified}"

    def test_transition_table_size(self):
        """TRANSITION_TABLE contains exactly 64 entries."""
        assert len(TRANSITION_TABLE) == 64, (
            f"Expected 64 entries, got {len(TRANSITION_TABLE)}"
        )

    def test_legal_illegal_counts(self):
        """The table has exactly 45 legal and 19 illegal transitions."""
        legal = sum(1 for v in TRANSITION_TABLE.values() if v)
        illegal = sum(1 for v in TRANSITION_TABLE.values() if not v)
        assert legal == 45, f"Expected 45 legal, got {legal}"
        assert illegal == 19, f"Expected 19 illegal, got {illegal}"

    def test_deleted_is_terminal(self):
        """deleted has no outgoing transitions except self."""
        for to_s in SORTED_STATES:
            if to_s == "deleted":
                assert validate_transition("deleted", "deleted") is True
            else:
                assert validate_transition("deleted", to_s) is False, (
                    f"deleted -> {to_s} should be illegal (terminal state)"
                )

    def test_deleted_outgoing_count(self):
        """deleted has exactly 1 legal outgoing transition (self)."""
        outgoing = sum(
            1 for to_s in SORTED_STATES
            if validate_transition("deleted", to_s)
        )
        assert outgoing == 1, (
            f"deleted should have exactly 1 outgoing (self), got {outgoing}"
        )

    def test_not_invoked_unreachable(self):
        """not_invoked has no incoming transitions except self."""
        for from_s in SORTED_STATES:
            if from_s == "not_invoked":
                assert validate_transition("not_invoked", "not_invoked") is True
            else:
                assert validate_transition(from_s, "not_invoked") is False, (
                    f"{from_s} -> not_invoked should be illegal (initial state)"
                )

    def test_not_generated_unreachable(self):
        """not_generated has no incoming transitions except self."""
        for from_s in SORTED_STATES:
            if from_s == "not_generated":
                assert validate_transition("not_generated", "not_generated") is True
            else:
                assert validate_transition(from_s, "not_generated") is False, (
                    f"{from_s} -> not_generated should be illegal (initial state)"
                )

    def test_initial_states_incoming_count(self):
        """Each initial state has exactly 1 legal incoming transition (self)."""
        for init_s in _INITIAL_STATES:
            incoming = sum(
                1 for from_s in SORTED_STATES
                if validate_transition(from_s, init_s)
            )
            assert incoming == 1, (
                f"Initial state {init_s!r} should have exactly 1 incoming "
                f"(self), got {incoming}"
            )

    def test_self_transitions_legal(self):
        """Every state can self-transition (idempotent re-assignment)."""
        for state in SORTED_STATES:
            assert validate_transition(state, state) is True, (
                f"Self-transition {state} -> {state} should be legal"
            )

    def test_active_states_fully_connected(self):
        """All active (non-initial, non-terminal) states can reach each other."""
        active_states = [
            s for s in SORTED_STATES
            if s not in _INITIAL_STATES and s not in _TERMINAL_STATES
        ]
        for from_s in active_states:
            for to_s in active_states:
                assert validate_transition(from_s, to_s) is True, (
                    f"Active states should be fully connected: "
                    f"{from_s} -> {to_s} should be legal"
                )

    def test_initial_states_can_reach_active(self):
        """Initial states can transition to all active and terminal states."""
        active_and_terminal = [
            s for s in SORTED_STATES if s not in _INITIAL_STATES
        ]
        for init_s in _INITIAL_STATES:
            for target in active_and_terminal:
                assert validate_transition(init_s, target) is True, (
                    f"Initial state {init_s} should reach {target}"
                )

    def test_initial_states_cannot_cross(self):
        """One initial state cannot transition to the other initial state."""
        for init_a in _INITIAL_STATES:
            for init_b in _INITIAL_STATES:
                if init_a != init_b:
                    assert validate_transition(init_a, init_b) is False, (
                        f"{init_a} -> {init_b} should be illegal "
                        f"(cannot reach initial state from another)"
                    )


class TestInvalidStateHandling:
    """validate_transition rejects states not in V1_ABSENCE_STATES."""

    def test_invalid_from_state_raises(self):
        """Invalid from_state raises ValueError."""
        with pytest.raises(ValueError, match="Unknown from_state"):
            validate_transition("resolved", "unknown")

    def test_invalid_to_state_raises(self):
        """Invalid to_state raises ValueError."""
        with pytest.raises(ValueError, match="Unknown to_state"):
            validate_transition("unknown", "fake_state")

    def test_both_invalid_raises(self):
        """Both states invalid raises ValueError (from_state checked first)."""
        with pytest.raises(ValueError, match="Unknown from_state"):
            validate_transition("bogus_a", "bogus_b")

    def test_empty_string_raises(self):
        """Empty string is not a valid state."""
        with pytest.raises(ValueError):
            validate_transition("", "unknown")

    def test_none_raises(self):
        """None is not a valid state."""
        with pytest.raises((ValueError, TypeError)):
            validate_transition(None, "unknown")

    def test_legacy_alias_not_accepted(self):
        """Legacy alias 'pruned' is NOT accepted by validate_transition.

        validate_transition works on canonical state strings only.
        Normalization is a separate concern (normalize_absence_state).
        """
        with pytest.raises(ValueError, match="Unknown"):
            validate_transition("pruned", "deleted")

    def test_case_sensitivity(self):
        """State names are case-sensitive."""
        with pytest.raises(ValueError):
            validate_transition("Unknown", "deleted")
        with pytest.raises(ValueError):
            validate_transition("DELETED", "unknown")


class TestTransitionTableAgreesWithFunction:
    """TRANSITION_TABLE dict and validate_transition() must always agree."""

    @pytest.mark.parametrize("from_state", SORTED_STATES)
    @pytest.mark.parametrize("to_state", SORTED_STATES)
    def test_table_matches_function(self, from_state, to_state):
        """Every entry in TRANSITION_TABLE matches validate_transition()."""
        table_result = TRANSITION_TABLE[(from_state, to_state)]
        func_result = validate_transition(from_state, to_state)
        assert table_result == func_result, (
            f"TRANSITION_TABLE[({from_state!r}, {to_state!r})] = {table_result} "
            f"but validate_transition returns {func_result}"
        )
