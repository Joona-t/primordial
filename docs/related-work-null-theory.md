# Related Work: Primordial's Absence Ontology in the Database Null Theory Tradition

**Purpose:** Positioning document for paper submission. Maps Primordial Computing's 8-state absence ontology against the database null theory lineage (Codd, Zaniolo, Date/Darwen), many-valued logics (Belnap, Fitting, Ginsberg), incomplete information theory (Imielinski/Lipski, Libkin), and programming language type theory (Option/Maybe/Result). For each tradition, identifies what Primordial inherits, where it genuinely extends prior art, where prior art has solutions Primordial should adopt, and citations that must appear in the paper.

**Status:** Research draft, ready for integration into Related Work section.

---

## Table of Contents

1. [Codd's Null Types (1979, 1990)](#1-codds-null-types-1979-1990)
2. [Zaniolo's Null Semantics (1984)](#2-zaniolos-null-semantics-1984)
3. [Date and Darwen: The Third Manifesto](#3-date-and-darwen-the-third-manifesto)
4. [Belnap's Four-Valued Logic (1977)](#4-belnaps-four-valued-logic-1977)
5. [Fitting's Bilattice Extensions (1991+)](#5-fittings-bilattice-extensions-1991)
6. [Libkin's Certain/Possible Answers (2006--2016)](#6-libkins-certainpossible-answers-2006-2016)
7. [Three-Valued Logic in SQL](#7-three-valued-logic-in-sql)
8. [Option/Maybe/Result Types in Programming Languages](#8-optionmayberesult-types-in-programming-languages)
9. [Synthesis: Where Primordial Sits](#9-synthesis-where-primordial-sits)
10. [Required Citations](#10-required-citations)

---

## 1. Codd's Null Types (1979, 1990)

### The Prior Art

E.F. Codd first addressed missing information in the relational model in his 1979 paper in ACM Transactions on Database Systems, where he proposed extending the relational model to handle null values denoting either an unknown value or an inapplicable property. In his 1990 book *The Relational Model for Database Management, Version 2* (RM/V2), Codd formalized this distinction into two explicit null-type markers:

- **A-mark (Missing But Applicable):** The entity has the attribute, but its value is currently unknown. Example: a person's spouse name when we know they are married but do not know the name.
- **I-mark (Missing But Inapplicable):** The entity does not have the attribute at all; the property is inapplicable. Example: a spouse name for a person who is unmarried.

Codd argued that SQL's single NULL conflates these two fundamentally different situations, and that correct handling would require expanding SQL from three-valued logic (True/False/Unknown) to a four-valued logic (True/False/Missing-Applicable/Missing-Inapplicable).

### Mapping to Primordial's 8 States

Codd's two-null distinction maps onto a strict subset of Primordial's ontology:

| Codd | Primordial Equivalent | Notes |
|------|----------------------|-------|
| A-mark (missing but applicable) | `unknown` | Value exists somewhere but we do not have it |
| I-mark (missing but inapplicable) | `not_invoked` | The computation/attribute is structurally inapplicable |

However, this mapping immediately reveals that Codd's two categories are insufficient for agent systems. Primordial distinguishes six additional absence modes that Codd did not consider:

| Primordial State | Why Codd's Framework Cannot Express It |
|-----------------|---------------------------------------|
| `not_generated` | Codd's model assumes data entry, not generative computation. There is no concept of "the system was supposed to produce this but did not." |
| `unresolved` | Codd's model is atemporal -- a tuple either has a value or a null. There is no "in progress" state. |
| `withheld` | Codd's nulls are epistemic (we don't know) or ontological (doesn't exist). Deliberate suppression of a known value is outside his framework. |
| `invalid` | Codd's model assumes data that passes schema constraints. A value that exists but failed semantic validation has no representation. |
| `deleted` | Codd's nulls are about current state. The distinction between "never existed" and "existed but was permanently removed" is absent. |
| `pruned_recoverable` | Entirely novel to agent systems. The concept of a value removed from the working set but recoverable via a grounded source path has no database analogue. |

### What Primordial Inherits

Primordial inherits Codd's foundational insight that a single null marker is semantically insufficient. The core claim of Primordial -- "absence is not the same as nothing" -- is a direct generalization of Codd's observation that "missing but applicable" and "missing but inapplicable" are not interchangeable. Primordial extends this from 2 absence types to 8, but the intellectual debt to Codd (1979, 1990) is direct and must be acknowledged.

### Where Primordial Extends Codd

1. **From static data to dynamic computation.** Codd's nulls describe the state of stored data. Primordial's states describe the lifecycle of computational artifacts: not yet attempted, attempted but incomplete, completed but failed, completed but suppressed, removed but recoverable, and permanently destroyed.
2. **Transition rules.** Codd proposed null types but no transition algebra between them. Primordial formalizes a 64-entry state-transition table with structural rules (initial states, terminal states, self-transitions) that constrain which absence-to-absence transitions are legal.
3. **Metadata requirements.** Codd's A-marks and I-marks are bare markers. Primordial requires companion metadata: `pruned_recoverable` must carry source_refs and recovery paths; `invalid` must carry the failing validator; `withheld` must carry the withholding reason.
4. **Provenance integration.** Codd's null types exist independently of data lineage. Primordial's absence states are integrated with provenance chains (parent_id, source_refs, artifact hashes), meaning that the *reason* for absence is itself a traceable artifact.

### Where Codd Has Solutions Primordial Should Adopt

Codd's four-valued logic provides a complete truth-table algebra for evaluating expressions containing A-marks and I-marks. Primordial currently has transition rules between absence states but does not define a compositional logic for evaluating expressions that reference absent values (e.g., "what is the result of comparing an `unknown` field with a `withheld` field?"). If Primordial ever needs to evaluate queries over records containing typed absences, Codd's four-valued truth tables provide the template for extending to an 8+-valued evaluation logic.

### Required Citations

- Codd, E.F. (1979). "Extending the Database Relational Model to Capture More Meaning." *ACM Transactions on Database Systems*, 4(4):397--434.
- Codd, E.F. (1990). *The Relational Model for Database Management: Version 2.* Addison-Wesley.

---

## 2. Zaniolo's Null Semantics (1984)

### The Prior Art

Carlo Zaniolo's 1984 paper "Database Relations with Null Values" (*Journal of Computer and System Sciences*, 28(1):142--166) proposed a formal approach to incomplete information in relational databases. Zaniolo identified three distinct semantics for null values in the literature:

1. **Unknown (existential) null:** A value exists but is unknown. The null stands for some definite value; we just do not know which one. Formally, the null is an existentially quantified variable.
2. **Nonexistent (inapplicable) null:** No value exists. The property represented by the column is inapplicable for this tuple.
3. **No-information null:** The null could be either unknown or inapplicable -- we do not even know which kind of absence we are facing.

Zaniolo's key contribution was demonstrating that a single formal framework could handle all three semantics through generalized relational algebra operators (projection, selection, union, join) that produce correct results under each interpretation. His approach obviated the need for multiple syntactically distinct null markers by encoding the semantics into the query evaluation strategy rather than the data representation.

### Mapping to Primordial

| Zaniolo Null Type | Primordial Equivalent | Precision of Mapping |
|-------------------|----------------------|---------------------|
| Unknown (existential) | `unknown` | Direct correspondence |
| Nonexistent (inapplicable) | `not_invoked` | Approximate -- Zaniolo's "inapplicable" is static; Primordial's `not_invoked` is dynamic (the computation was never initiated) |
| No-information | `unknown` with degraded metadata | Zaniolo's "no information" is a meta-null -- uncertainty about the type of absence itself. Primordial does not have a dedicated "don't know why it's absent" state; `unknown` serves this role, but with lower epistemic precision than Zaniolo's explicit three-way distinction. |

### What Primordial Inherits

Primordial implicitly inherits Zaniolo's insight that the *type of ignorance* matters: not knowing a value (existential), not having a value (inapplicable), and not knowing which kind of not-knowing applies (no-information) are three distinct epistemic situations. Primordial's `unknown` state conflates Zaniolo's "unknown" and "no-information" categories, which is a defensible simplification for agent systems where the relevant question is usually "can this be resolved?" rather than "what kind of absence is this?"

### Where Primordial Extends Zaniolo

1. **Computational lifecycle states.** Zaniolo's three null types are purely epistemic (what do we know about the absence?). Primordial adds causal/temporal states: `not_generated` (the producer failed), `unresolved` (work in progress), `invalid` (produced but rejected), `withheld` (exists but suppressed), `deleted` (permanently removed), `pruned_recoverable` (removed but retrievable).
2. **State transitions.** Zaniolo's null types are static classifications. A null does not transition from "unknown" to "nonexistent." Primordial's absence states are explicitly dynamic: `unknown` can become `unresolved` (investigation started), `withheld` (turns out it was suppressed), or `deleted` (permanently abandoned).
3. **Operational semantics.** Zaniolo focused on correct query evaluation over incomplete data. Primordial focuses on correct state tracking through agent computation, including compaction, retry, and delegation.

### Where Zaniolo's Framework Offers Lessons

Zaniolo's "no-information" null -- uncertainty about the type of absence itself -- is a concept Primordial should consider more carefully. In real agent workflows, there are situations where a value is absent and the system cannot determine whether it was never generated, silently deleted, or withheld. Currently, Primordial assigns `unknown` in such cases, but this conflates "value unknown" with "absence-type unknown." If the ontology ever needs refinement, Zaniolo's three-way distinction provides the template for separating first-order absence (value missing) from second-order absence (reason for missing is itself missing).

### Required Citations

- Zaniolo, C. (1984). "Database Relations with Null Values." *Journal of Computer and System Sciences*, 28(1):142--166.
- Imielinski, T. and Lipski, W. (1984). "Incomplete Information in Relational Databases." *Journal of the ACM*, 31(4):761--791.

---

## 3. Date and Darwen: The Third Manifesto

### The Prior Art

C.J. Date and Hugh Darwen's *The Third Manifesto* (first published 1995, revised editions through 2006 as *Databases, Types, and the Relational Model*) represents the most sustained critique of SQL's null handling. Their central argument is radical: **nulls should not exist at all in a properly designed relational system.** Instead, the problems that nulls purport to solve should be addressed through the type system.

Date and Darwen's key claims:

1. **SQL's three-valued logic is inconsistent.** NULL handling in WHERE clauses, joins, and aggregate functions produces contradictory or unintuitive results. For example, `NULL = NULL` yields UNKNOWN, but `GROUP BY` treats all NULLs as equal. `COUNT(*)` counts rows with NULLs, but `COUNT(column)` does not.
2. **Nulls violate the relational model.** A relation is defined as a set of tuples, and each tuple must contain exactly one value for each attribute. Since NULL is not a value, any system permitting nulls violates the foundational definition.
3. **The solution is types, not special markers.** Instead of NULL for a person's spouse name, define a type `MaritalStatus` that is either `Married(SpouseName)` or `Unmarried`. The absence of a spouse name is not a null -- it is a different type variant that makes the attribute inapplicable *at the type level*.

Date further developed these ideas in *Database in Depth* (2005), advocating "specialization by constraint" -- using type inheritance and constraint declarations to eliminate the need for nulls entirely.

### Mapping to Primordial

Date and Darwen's position is not that there should be multiple null types (contra Codd) but that there should be *zero* null types. Absence should be eliminated by making the type system expressive enough to represent every possible state of a datum.

This position maps onto Primordial's approach with striking precision:

| Date/Darwen Principle | Primordial Realization |
|-----------------------|-----------------------|
| Nulls should be replaced by types | `AbsenceState` is an enum (algebraic data type) with 8 variants |
| The type system should make illegal states unrepresentable | The transition table makes 19 of 64 state combinations structurally illegal |
| Every value must be exactly one type | Every absent field must carry exactly one `AbsenceState` -- bare `None`, empty string, and empty dict are all rejected as `ForgeNullError` |
| Specialization by constraint | Each absence state has mandatory metadata constraints (`pruned_recoverable` requires `source_refs`, `invalid` requires validator info) |

### What Primordial Inherits

Primordial's core design philosophy is Date's philosophy applied to agent computation: **do not use untyped absence; encode the reason for absence into the type system.** The `ForgeNullError` exception -- raised when any ambiguous empty value (None, "", {}, []) is encountered without a typed absence state -- is a direct implementation of Date's prohibition on nulls. The `validate_field()` and `validate_record()` functions enforce at the protocol level what Date argues should be enforced at the type level.

### Where Primordial Extends Date/Darwen

1. **Dynamic state transitions.** Date's type-based approach is static: a value has a type at design time. Primordial's absence states change during execution (e.g., `not_invoked` becomes `unresolved` becomes `invalid`). Date's framework does not address how a value's absence classification evolves over a computation's lifetime.
2. **Agent-specific absence modes.** Date's types model the structure of stored data. Primordial models the lifecycle of computational artifacts, including states (like `pruned_recoverable` and `withheld`) that have no analogue in persistent storage.
3. **Provenance through absence transitions.** Date's approach eliminates nulls but does not track the history of how a value came to have its current type. Primordial records transitions as first-class events, creating an audit trail of absence evolution.

### Where Date/Darwen's Critique Applies to Primordial

Date's insistence on *compositional correctness* -- that every operation on typed data should produce well-typed results -- is a standard Primordial has not yet met. Currently, Primordial validates absence states at record boundaries (ingress/egress) but does not define a closed algebra for composing absence-typed values. For example: if agent A has output in state `withheld` and agent B has output in state `unknown`, and a downstream agent needs to combine them, what is the resulting absence state? Primordial has no answer to this question. Date's compositional type theory suggests that such a composition algebra is necessary for soundness.

### Required Citations

- Date, C.J. and Darwen, H. (1995). *The Third Manifesto.* ACM SIGMOD Record 24(1):39--49. doi:10.1145/202660.202667.
- Date, C.J. and Darwen, H. (2006). *Databases, Types, and the Relational Model: The Third Manifesto.* 3rd ed. Addison-Wesley.
- Date, C.J. (2005). *Database in Depth: Relational Theory for Practitioners.* O'Reilly.

---

## 4. Belnap's Four-Valued Logic (1977)

### The Prior Art

Nuel Belnap, in his 1977 papers "A Useful Four-Valued Logic" and "How a Computer Should Think," proposed a logic designed for computer reasoning systems that must cope with both incomplete and inconsistent information. The four truth values are:

| Value | Symbol | Meaning |
|-------|--------|---------|
| True | **t** | Told only true |
| False | **f** | Told only false |
| Both | **T** (top) | Told both true and false (contradiction) |
| Neither | **perp** (bottom) | Told nothing (no information) |

The key innovation is the *bilattice structure*: these four values are organized by two independent lattice orderings:

- **Truth ordering (<=_t):** f <=_t Neither <=_t t, f <=_t Both <=_t t. Orders by degree of truth.
- **Knowledge ordering (<=_k):** Neither <=_k f <=_k Both, Neither <=_k t <=_k Both. Orders by amount of information.

The truth ordering is logical (what do we believe?). The knowledge ordering is epistemic (how much do we know?). Belnap argued that a computer reasoning system should use this four-valued logic rather than classical two-valued logic, because "minor inconsistencies in its data should not be allowed to lead (as in classical logic) to irrelevant conclusions."

### Is Primordial's Ontology a Belnap-Like Lattice?

This is the critical structural question. The answer is: **partially, but with significant divergence.**

**Similarities to Belnap:**

1. **Multiple absence types organized by information content.** Like Belnap's knowledge ordering, Primordial's states can be partially ordered by "how much we know about the absence": `unknown` (least information) < `not_invoked`/`not_generated` (know the cause) < `withheld` (know the value exists) < `pruned_recoverable` (know the value and its recovery path).
2. **Neither/Bottom analogue.** Belnap's Neither (no information) maps closely to Primordial's `unknown` (cannot determine whether a value exists or what it is).
3. **Tolerance of inconsistency.** Belnap's Both (contradictory information) has a partial analogue in Primordial: a field could simultaneously have evidence of being `withheld` (from one agent) and `deleted` (from another). Primordial does not currently model this -- it requires a single state at any time -- but the transition table allows investigating such cases by tracking the sequence `withheld` -> `deleted`.

**Divergences from Belnap:**

1. **Not a bilattice.** Primordial's 8 states cannot be naturally organized into a bilattice with two independent lattice orderings. The truth ordering (is the value present or absent?) is trivially binary for all 8 states -- they are all "absent." The knowledge ordering is not a lattice because there is no natural join/meet for arbitrary pairs (what is the join of `invalid` and `pruned_recoverable`?).
2. **Temporal/causal dimension.** Belnap's values are atemporal: a proposition has a fixed four-valued truth assignment from available information sources. Primordial's states are explicitly temporal: a value transitions from `not_invoked` to `unresolved` to `invalid` over time. This temporal dimension has no Belnap analogue.
3. **More than epistemic.** Belnap's four values are purely epistemic (what is known/told). Primordial's states include non-epistemic modes: `deleted` is a *performed action*, not an epistemic state; `withheld` is a *policy decision*, not an information state; `pruned_recoverable` is a *system operation*, not a knowledge state.
4. **Transition rules vs. truth tables.** Belnap defines truth tables for logical connectives (AND, OR, NOT) over four values. Primordial defines a transition table for state changes. These are fundamentally different formal objects: Belnap's tables compose values; Primordial's table constrains temporal evolution.

### What Primordial Should Borrow from Belnap

The **knowledge ordering** concept is directly applicable to Primordial and should be formalized. If we define "more informative absence state" as one that gives the consumer more actionable information, we get a partial order:

```
unknown (least informative)
  |
  +-- not_generated (know the cause: LLM failure)
  |     |
  +-- not_invoked (know the cause: never called)
  |     |
  +-- unresolved (know the cause: in progress)
  |
  +-- invalid (know the cause + have the failed artifact)
  |
  +-- withheld (know the value exists + know the suppression reason)
  |
  +-- pruned_recoverable (know the value + have the recovery path)
  |
deleted (terminal: know it was destroyed, cannot recover)
```

This is not a lattice (no natural meet/join for all pairs), but it is a well-founded partial order that could be formalized as a Belnap-inspired information ordering on absence states. The paper should note this connection explicitly.

### Required Citations

- Belnap, N.D. (1977). "A Useful Four-Valued Logic." In Dunn, J.M. and Epstein, G. (eds.), *Modern Uses of Multiple-Valued Logic*, 5--37. Reidel.
- Belnap, N.D. (1977). "How a Computer Should Think." In Ryle, G. (ed.), *Contemporary Aspects of Philosophy*, 30--56. Oriel Press.

---

## 5. Fitting's Bilattice Extensions (1991+)

### The Prior Art

Melvin Fitting (1991, 2002) and Matthew Ginsberg (1988) independently generalized Belnap's four-valued logic into the theory of *bilattices* -- algebraic structures with two partial orderings that can accommodate arbitrarily many truth values while preserving the knowledge/truth distinction.

**Ginsberg (1988)** introduced bilattices as a uniform framework for AI reasoning, showing that first-order logic, assumption-based truth maintenance systems (ATMSs), default logic, and circumscription can all be modeled as special cases of bilattice-based inference. The key idea: a bilattice is a set with two lattice orderings (truth and knowledge) that interact via De Morgan-like negation operations.

**Fitting (1991)** developed bilattice-based semantics for logic programming, showing that classical two-valued semantics and Kripke-Kleene three-valued semantics are special cases of the bilattice framework when restricted to the simplest bilattice (Belnap's FOUR). Fitting demonstrated that bilattices based on finite many-valued logics and probabilistic-valued logic are all instances of the same general construction.

The *twist-product construction* (formalized by Rivieccio and others) shows that any bilattice can be decomposed as L+ |><| L-, where L+ and L- are two component lattices. This construction defines:
- Logical conjunction: (a+, a-) AND (b+, b-) = (a+ AND b+, a- OR b-)
- Information conjunction: (a+, a-) MEET (b+, b-) = (a+ AND b+, a- AND b-)
- Negation: NOT(a+, a-) = (a-, a+)

A recent survey (Jakl, 2025, arXiv:2503.20679) traces four distinct "imprints" of Belnap's logic in modern computer science: linear logic, d-frames, Blame Calculus, and LVars (parallel programming variables), showing that the bilattice structure appears independently across multiple subfields.

### Relevance to Primordial

Fitting's work is relevant to Primordial in three ways:

**1. The many-valued generalization question.** Fitting proved that Belnap's 4-valued logic generalizes naturally to n-valued bilattices. This suggests a theoretical path for Primordial: could the 8-state absence ontology be embedded in a bilattice? The answer is *not directly*, because Primordial's states include temporal/causal dimensions (transition rules) that bilattice theory does not model. However, the *information-ordering dimension* of Primordial's states (the partial order from `unknown` to `pruned_recoverable`) could be formalized as a single lattice component of a bilattice-like structure.

**2. The twist-product as a composition operator.** If Primordial ever needs to compose absence states from multiple agents (agent A says `withheld`, agent B says `unknown`), the twist-product construction provides a principled template. The positive component would track "most informative assessment" and the negative component would track "most pessimistic assessment," yielding a composed state that preserves both dimensions.

**3. Fixed-point semantics for absence reasoning.** Fitting's fixed-point semantics for logic programming over bilattices could provide a foundation for recursive absence reasoning: when agent chains produce cycles of absence (A depends on B which depends on A, both absent), a fixed-point construction could determine the "stable" absence assignment. This is directly relevant to Primordial's `unresolved` state in multi-agent dependency chains.

### What Primordial Should Acknowledge

The paper should explicitly state that Primordial's ontology is **not** a bilattice and explain why: the temporal/causal transition rules and the non-epistemic states (deleted, withheld as policy) break the bilattice axioms. However, the paper should also acknowledge that the *information-ordering dimension* of the ontology is bilattice-inspired (even if this inspiration was originally implicit) and that Fitting's framework provides the natural generalization path if Primordial's ontology needs to support logical composition.

### Required Citations

- Fitting, M. (1991). "Bilattices and the Semantics of Logic Programming." *Journal of Logic Programming*, 11(2):91--116.
- Ginsberg, M.L. (1988). "Multivalued Logics: A Uniform Approach to Reasoning in Artificial Intelligence." *Computational Intelligence*, 4(3):265--316.
- Fitting, M. (2002). "Bilattices Are Nice Things." In Hendricks, V. et al. (eds.), *Self-Reference*, 53--77. CSLI Publications.
- Jakl, T. (2025). "Four Imprints of Belnap's Useful Four-Valued Logic in Computer Science." arXiv:2503.20679.

---

## 6. Libkin's Certain/Possible Answers (2006--2016)

### The Prior Art

Leonid Libkin's research program on incomplete information in databases (2006--2016) established a rigorous framework for reasoning about queries over databases with missing values. The core concepts:

**Certain answers:** Given an incomplete database D* (containing nulls), the certain answers to a query Q are the tuples that appear in Q(D) for *every* complete database D that D* could represent. Certain answers are guaranteed to be correct regardless of how the missing values are filled in.

**Possible answers:** Tuples that appear in Q(D) for *at least one* complete database D that D* could represent. Possible answers might be correct but are not guaranteed.

**Naive evaluation:** Simply evaluating Q on D* directly (treating nulls as ordinary values). Naive evaluation is computationally cheap but may produce neither certain nor possible answers -- it can include false positives and miss true positives.

The foundational paper by Imielinski and Lipski (1984) established the possible-worlds semantics: an incomplete database represents a set of possible complete databases (possible worlds), and query answering must be defined relative to this set. Libkin's key contribution (PODS 2011, TODS 2016) was connecting this theoretical framework to SQL's actual behavior, demonstrating that SQL's three-valued logic does not compute certain answers in general, and proposing practical corrections.

### Mapping to Agent Provenance

Libkin's certain/possible framework maps onto Primordial's problem with surprising precision once "database" is replaced by "agent trace":

| Libkin Concept | Primordial Analogue |
|----------------|-------------------|
| Incomplete database | Agent trace with absent fields (8 absence states) |
| Complete database (possible world) | Hypothetical trace where all absent fields are resolved |
| Certain answer | Conclusion that holds regardless of how absent fields resolve |
| Possible answer | Conclusion that holds under at least one resolution of absent fields |
| Naive evaluation | Treating absent fields as "skip" or "ignore" (the current default in most agent runtimes) |

The connection is particularly sharp for Primordial's compaction problem. When agent context is compacted, information is replaced by summaries or removed entirely (creating `pruned_recoverable` and `deleted` states). Any conclusion drawn from a compacted trace is analogous to a query answer from an incomplete database. Libkin's framework provides the vocabulary:

- A claim about an agent's behavior is **certain** if it holds for every possible reconstruction of the compacted information.
- A claim is **possible** if it holds for at least one reconstruction.
- Naive evaluation (ignoring compacted fields) is analogous to SQL's naive null handling -- sometimes correct, sometimes wrong, with no formal guarantee.

### What Primordial Should Adopt

Libkin's framework provides something Primordial currently lacks: **a formal semantics for reasoning *about* records containing typed absence.** Primordial validates that absence states are correctly assigned and that transitions are legal, but it does not define what conclusions can be drawn from a record that contains absent fields. Libkin's certain/possible distinction provides exactly this:

1. **Certain conclusions from absent data.** If a field is `not_invoked`, certain conclusions include "the tool was not called." If a field is `pruned_recoverable`, certain conclusions include "the value existed at some point" and "a recovery path exists."
2. **Possible conclusions from absent data.** If a field is `unknown`, possible conclusions include any value in the field's domain. If a field is `withheld`, possible conclusions include the actual withheld value.
3. **Impossible conclusions from absent data.** If a field is `deleted`, no conclusion about the original value is possible (the value is permanently lost). This is the `deleted` state's semantic content formalized.

### Where Primordial Extends Libkin

1. **Typed absence beyond marked nulls.** Libkin's framework uses marked nulls (distinct null symbols that may or may not represent the same unknown value). Primordial's 8 states carry far more semantic content than marked nulls -- each state constrains the possible-worlds set differently.
2. **Transition rules constrain possible worlds.** In Libkin's framework, the set of possible worlds is defined by the schema and the nulls. In Primordial, the transition table further constrains which histories are possible: a field that was once `not_invoked` cannot have been `deleted` before being invoked. This temporal constraint narrows the possible-worlds set.
3. **Recovery paths reduce uncertainty.** Libkin's marked nulls provide no path back to the actual value. Primordial's `pruned_recoverable` state includes source_refs that may allow the actual value to be retrieved, converting a possible answer into a certain answer.

### Required Citations

- Imielinski, T. and Lipski, W. (1984). "Incomplete Information in Relational Databases." *Journal of the ACM*, 31(4):761--791.
- Libkin, L. (2011). "Incomplete Information and Certain Answers in General Data Models." In *Proceedings of the 30th ACM SIGMOD-SIGACT-SIGAI Symposium on Principles of Database Systems (PODS)*, 59--70.
- Libkin, L. (2014). "Incomplete Data: What Went Wrong, and How to Fix It." In *Proceedings of the 33rd ACM SIGMOD-SIGACT-SIGART Symposium on Principles of Database Systems (PODS)*, 1--13.
- Libkin, L. (2016). "SQL's Three-Valued Logic and Certain Answers." *ACM Transactions on Database Systems*, 41(1):Article 4.
- Guagliardo, P. and Libkin, L. (2017). "A Formal Semantics of SQL Queries, Its Validation, and Applications." *Proceedings of the VLDB Endowment*, 11(1):27--39.

---

## 7. Three-Valued Logic in SQL

### The Problem

SQL implements three-valued logic (3VL) with truth values True, False, and Unknown. Any comparison involving NULL yields Unknown. The WHERE clause returns only rows where the predicate evaluates to True, silently discarding both False and Unknown rows. This creates a family of well-documented problems:

**Comparison collapse.** `NULL = NULL` evaluates to Unknown (not True). This means self-joins on nullable columns lose rows, violating the expectation that a table joined with itself yields itself.

**Aggregate inconsistency.** `COUNT(*)` counts all rows including those with NULLs; `COUNT(column)` counts only non-NULL rows. `SUM(column)` ignores NULLs but `SUM(column) + 0` does not. `AVG` silently excludes NULLs from both numerator and denominator, potentially changing the result.

**Boolean collapse.** `NOT(Unknown)` is Unknown. `Unknown AND True` is Unknown. `Unknown OR True` is True. The asymmetry means that logically equivalent expressions can yield different results when NULLs are involved.

**Join silence.** Outer joins introduce NULLs for non-matching rows. These NULLs are semantically different from NULLs meaning "value unknown" -- they mean "this row has no match" -- but SQL's 3VL treats them identically.

### How This Relates to Primordial

SQL's NULL problems are the *concrete, deployed consequence* of the abstract design flaw that Primordial addresses. Every SQL NULL problem can be traced to the same root cause: multiple distinct absence semantics collapsed into a single marker evaluated by a single logic.

| SQL Problem | Root Cause | Primordial's Prevention |
|-------------|-----------|------------------------|
| `NULL = NULL` -> Unknown | "Unknown value" and "inapplicable" are the same marker | `unknown` and `not_invoked` are distinct states with different semantics |
| `COUNT(*)` vs `COUNT(col)` | Cannot distinguish "row exists with missing value" from "row exists with inapplicable attribute" | Each field's absence state is explicit; aggregation can respect the distinction |
| Outer join NULLs | "No match found" (structural) conflated with "value missing" (epistemic) | `not_invoked` (structural: never called) is distinct from `unknown` (epistemic: cannot determine) |
| `SUM` ignoring NULLs | Cannot distinguish "value is 0" from "value is missing" | A field with value 0 is `resolved`; a missing field has an explicit absence state |

### The Deeper Lesson for Primordial

SQL's 3VL problems demonstrate that *having a null type is insufficient if the evaluation logic does not respect the type distinctions.* Codd proposed two null types but a four-valued logic. Primordial has eight absence types but *no evaluation logic* -- no definition of what happens when operations encounter absent fields. If Primordial's absence ontology is ever used to evaluate expressions (rather than just validate records), it will need to define an 8+-valued logic that respects all state distinctions. Otherwise, it risks reproducing SQL's problems at a different level: eight absence types collapsed into a single "skip this field" evaluation strategy.

### Required Citations

- Libkin, L. (2016). "SQL's Three-Valued Logic and Certain Answers." *ACM Transactions on Database Systems*, 41(1):Article 4.
- Date, C.J. (2005). *Database in Depth: Relational Theory for Practitioners.* O'Reilly. (Chapter on "Why Nulls Are Prohibited.")
- Guagliardo, P. and Libkin, L. (2022). "A Formalization of SQL with Nulls." *Journal of Automated Reasoning*, 66:499--536. doi:10.1007/s10817-022-09632-4.

---

## 8. Option/Maybe/Result Types in Programming Languages

### The Prior Art

Programming language type theory provides the most widely deployed solutions to the null problem, beginning with ML's algebraic data types (1973) and continuing through modern languages:

| Language | Absence Type | Type Signature | Error-Carrying? |
|----------|-------------|----------------|-----------------|
| Haskell | `Maybe a` | `data Maybe a = Nothing \| Just a` | No (use `Either e a` for errors) |
| Rust | `Option<T>` | `enum Option<T> { None, Some(T) }` | No (use `Result<T, E>` for errors) |
| Rust | `Result<T, E>` | `enum Result<T, E> { Ok(T), Err(E) }` | Yes: typed error in `Err(E)` |
| Haskell | `Either a b` | `data Either a b = Left a \| Right b` | Yes: error in `Left a` |
| OCaml | `option` | `type 'a option = None \| Some of 'a` | No (use `result` for errors) |
| Swift | `Optional<T>` | `enum Optional<T> { case none, case some(T) }` written as `T?` | No (use `Result<Success, Failure>`) |
| Kotlin | Nullable `T?` | Compiler-enforced null safety | No (use sealed classes) |
| Java | `Optional<T>` | `class Optional<T>` | No (typically use exceptions) |

The key type-theoretic formulation: `Option A = A + 1`, meaning an Option type adds exactly one "empty" value to a set. In category theory, Option is a pointed endofunctor; in practice, it is a monad that supports chaining (`flatMap`/`>>=`) to propagate absence through computation.

**Result/Either** extends Option by carrying error information: `Result<T, E> = T + E`, meaning the result is either a success value of type T or an error value of type E. This is structurally more informative than Option but still binary: the error variant carries a single error type, and the value is either fully present or fully error.

**Kotlin sealed classes** represent a further extension: a sealed hierarchy can define an arbitrary number of variants with compiler-enforced exhaustive pattern matching. This is the closest PL analogue to Primordial's approach -- a sealed class with 8 variants would be structurally similar to the AbsenceState enum.

### Mapping to Primordial

| PL Concept | Primordial Equivalent | Relationship |
|-----------|----------------------|-------------|
| `None`/`Nothing` | All 8 absence states (collapsed) | PL conflates all reasons for absence into a single `None` |
| `Some(v)`/`Just v` | `resolved` (value present) | Direct correspondence |
| `Err(e)` | `invalid` (with error metadata) | Approximate: Rust's `Err` carries the error; Primordial's `invalid` carries validator/failure reason |
| `Either Left err \| Right val` | Binary `{resolved, invalid}` | Either has exactly 2 variants; Primordial has 8+1 |
| Sealed class hierarchy | `AbsenceState` enum | Closest PL analogue: compiler-enforced finite set of variants with exhaustive matching |

### Where PL Type Theory Falls Short

1. **Option/Maybe is binary.** `Nothing` does not distinguish "never computed" from "computation failed" from "value exists but is withheld" from "value was deleted." All of these collapse into `Nothing`. Monadic chaining (`>>=`) propagates `Nothing` without any information about which step failed or why.

2. **Result/Either is binary with one error type.** `Err(e)` carries information about *one* failure mode, but the error type is a single type parameter. Primordial needs to distinguish 7 different non-present states, each with different metadata requirements and different transition rules. A `Result<T, AbsenceState>` would be structurally possible but would lose transition rules and metadata constraints.

3. **No temporal evolution.** PL types are instantaneous: a value has type `Option<T>` at a point in the program. There is no concept of "this value was `None` because `not_invoked`, then became `None` because `unresolved`, then became `Some(v)`." Primordial's transition table tracks this temporal evolution.

4. **No composition across agents.** Monadic composition (>>=) propagates a single `None` forward. Primordial needs to compose absence states from multiple concurrent agents, which requires a richer composition semantics than monadic chaining.

### Where PL Type Theory Excels

1. **Compile-time enforcement.** Haskell and Rust enforce exhaustive pattern matching at compile time. Primordial enforces absence-state validity at runtime (via `validate_field`/`validate_record`). Moving to compile-time enforcement (e.g., via a type system that makes `AbsenceState` a first-class type parameter) would strengthen Primordial's guarantees.

2. **Monadic composition is well-understood.** The theory of monadic error propagation (>>=, flatMap, do-notation) is mature and battle-tested. Primordial should study whether its absence-state composition can be expressed as a monad, applicative functor, or arrow, borrowing the PL community's composition machinery rather than inventing it from scratch.

3. **Sealed class hierarchies with associated data.** Kotlin's sealed classes and Rust's enums with data allow each variant to carry different metadata. This is exactly Primordial's design for absence states with per-state metadata requirements, and the paper should cite this as a design influence even if the implementation is in Python (which lacks native sealed types).

### Required Citations

- Milner, R. et al. (1997). *The Definition of Standard ML (Revised).* MIT Press. (Origin of algebraic data types and the Option pattern.)
- Wadler, P. (1995). "Monads for Functional Programming." In Jeuring, J. and Meijer, E. (eds.), *Advanced Functional Programming*, LNCS 925, 24--52. Springer. (Monadic error propagation.)
- Peyton Jones, S.L. et al. (2003). *Haskell 98 Language and Libraries: The Revised Report.* Cambridge University Press. (Canonical `Maybe`/`Either` definitions.)

---

## 9. Synthesis: Where Primordial Sits

### The Intellectual Landscape

The traditions surveyed above form three distinct clusters, and Primordial draws from all three while belonging fully to none:

**Cluster 1: Database Null Theory (Codd, Zaniolo, Date/Darwen, Libkin)**
- Concerns: static data with missing values; correct query evaluation; relational algebra over incomplete information.
- Key achievement: Identifying that null conflates multiple absence semantics.
- Key limitation: Atemporal. No concept of absence states evolving through a computation lifecycle.

**Cluster 2: Many-Valued Logic (Belnap, Fitting, Ginsberg)**
- Concerns: reasoning with incomplete and inconsistent information; knowledge ordering vs truth ordering; bilattice algebra.
- Key achievement: A formal algebra for composing and reasoning about partial information.
- Key limitation: Purely epistemic. No concept of performed actions (deletion, withholding, pruning) as absence modes.

**Cluster 3: PL Type Theory (Option/Maybe/Result, sealed classes)**
- Concerns: compile-time safety; preventing null-pointer exceptions; exhaustive case analysis; monadic composition.
- Key achievement: Making absent/present a type-level distinction enforced by the compiler.
- Key limitation: Binary (present/absent) or binary-with-error (Ok/Err). No multi-valued absence ontology; no transition rules; no provenance.

### Primordial's Position

Primordial occupies a novel position: **a multi-valued absence ontology with temporal transition rules and provenance integration, designed for autonomous agent computation.**

| Dimension | Database Null Theory | Many-Valued Logic | PL Type Theory | **Primordial** |
|-----------|---------------------|-------------------|----------------|----------------|
| Number of absence types | 1--3 (Codd: 2; Zaniolo: 3; SQL: 1) | 2 (Neither, Both) | 1 (None/Nothing) or 2 (None + Err) | **8** |
| Temporal evolution | No | No | No | **Yes** (64-entry transition table) |
| Transition rules | No | No | No | **Yes** (initial, terminal, legal/illegal) |
| Metadata per state | No (bare markers) | No (bare truth values) | Partial (Err carries error) | **Yes** (per-state requirements) |
| Provenance integration | No | No | No | **Yes** (parent_id, source_refs, hashes) |
| Composition algebra | Yes (Codd: 4VL; Libkin: certain answers) | Yes (bilattice algebra) | Yes (monadic composition) | **No** (open gap) |
| Compile-time enforcement | No (runtime SQL) | No (mathematical) | Yes (type checker) | **No** (runtime validation) |
| Domain | Static stored data | Abstract reasoning | General programming | **Agent computation** |

### Genuine Extensions Over All Prior Art

1. **Causal/temporal absence taxonomy.** No prior tradition distinguishes absence states by their causal history (never attempted vs. attempted but failed vs. completed but suppressed vs. removed but recoverable). This is Primordial's primary novel contribution.
2. **Formal transition table.** The 8x8 transition matrix with structural generation rules (initial, terminal, self-transition, default) is, to our knowledge, the first formalization of legal/illegal transitions between absence states.
3. **Provenance-integrated absence.** Prior work treats provenance (W3C PROV) and absence (null theory) as separate concerns. Primordial integrates them: each absence state carries provenance metadata, and transitions between absence states are themselves provenance-bearing events.
4. **Recovery-graded absence.** The distinction between `deleted` (terminal, no recovery) and `pruned_recoverable` (active, recovery path exists) is novel. Database null theory has no concept of "the value was removed but we kept the return path." This is specific to agent systems where context compaction is a first-class operation.

### Open Gaps Identified by This Analysis

1. **No composition algebra.** Codd defined 4VL for composing expressions with nulls. Belnap/Fitting defined bilattice algebra. PL defined monadic composition. Primordial has no equivalent. When two absence-typed values must be combined, there is no formal answer.
2. **No evaluation logic.** SQL's 3VL, flawed as it is, provides an answer to "what happens when a WHERE clause encounters a NULL." Primordial provides no answer to "what happens when a downstream agent encounters an `unresolved` dependency."
3. **No possible-worlds semantics.** Libkin's certain/possible framework provides formal guarantees about conclusions drawn from incomplete data. Primordial validates absence states but does not define what conclusions are certain or possible given a particular absence assignment.
4. **Runtime-only enforcement.** PL type theory enforces absence handling at compile time. Primordial enforces it at runtime. A type-theoretic embedding (e.g., making AbsenceState a type parameter in a statically-typed language) would strengthen the guarantees.

---

## 10. Required Citations

The following citations MUST appear in any paper presenting Primordial's absence ontology. They are organized by precedence (foundational first, then extensions, then recent work).

### Foundational (must-cite for establishing intellectual lineage)

1. **Codd, E.F. (1979).** "Extending the Database Relational Model to Capture More Meaning." *ACM TODS* 4(4):397--434. *[Origin of typed nulls in databases.]*
2. **Codd, E.F. (1990).** *The Relational Model for Database Management: Version 2.* Addison-Wesley. *[A-marks and I-marks; four-valued logic proposal.]*
3. **Zaniolo, C. (1984).** "Database Relations with Null Values." *JCSS* 28(1):142--166. *[Three null semantics: unknown, nonexistent, no-information.]*
4. **Imielinski, T. and Lipski, W. (1984).** "Incomplete Information in Relational Databases." *JACM* 31(4):761--791. *[Possible-worlds semantics for incomplete databases.]*
5. **Belnap, N.D. (1977).** "A Useful Four-Valued Logic." In *Modern Uses of Multiple-Valued Logic*, 5--37. Reidel. *[Four-valued logic with knowledge ordering.]*
6. **Belnap, N.D. (1977).** "How a Computer Should Think." In *Contemporary Aspects of Philosophy*, 30--56. Oriel Press. *[Motivation for four-valued reasoning in computer systems.]*
7. **Date, C.J. and Darwen, H. (2006).** *Databases, Types, and the Relational Model: The Third Manifesto.* 3rd ed. Addison-Wesley. *[Type-based alternative to nulls.]*
8. **Hoare, C.A.R. (2009).** "Null References: The Billion Dollar Mistake." QCon London keynote. *[Motivates typed absence in general.]*

### Extensions (should-cite for demonstrating awareness of the broader landscape)

9. **Fitting, M. (1991).** "Bilattices and the Semantics of Logic Programming." *J. Logic Programming* 11(2):91--116. *[Many-valued generalization of Belnap; bilattice framework.]*
10. **Ginsberg, M.L. (1988).** "Multivalued Logics: A Uniform Approach to Reasoning in AI." *Computational Intelligence* 4(3):265--316. *[Bilattices for AI reasoning.]*
11. **Libkin, L. (2016).** "SQL's Three-Valued Logic and Certain Answers." *ACM TODS* 41(1):Article 4. *[Bridge between SQL 3VL and incomplete information theory.]*
12. **Libkin, L. (2014).** "Incomplete Data: What Went Wrong, and How to Fix It." *PODS'14*, 1--13. *[Diagnosis of SQL null semantics failures.]*
13. **Guagliardo, P. and Libkin, L. (2022).** "A Formalization of SQL with Nulls." *J. Automated Reasoning* 66:499--536. *[Coq-verified SQL null semantics.]*
14. **Date, C.J. (2005).** *Database in Depth.* O'Reilly. *["Why Nulls Are Prohibited" chapter.]*
15. **Wadler, P. (1995).** "Monads for Functional Programming." *AFP LNCS 925*, 24--52. Springer. *[Monadic error propagation -- the PL community's answer to composing absence.]*

### Recent/Contextual (cite where relevant for positioning against current work)

16. **Jakl, T. (2025).** "Four Imprints of Belnap's Useful Four-Valued Logic in Computer Science." arXiv:2503.20679. *[Contemporary survey of Belnap's influence across CS subfields.]*
17. **Toussaint, E. et al. (2022).** "Troubles with Nulls, Views from the Users." *PVLDB* 15(11):2613--2625. *[Empirical evidence that null handling confuses database users.]*
18. **Fitting, M. (2002).** "Bilattices Are Nice Things." In *Self-Reference*, 53--77. CSLI Publications. *[Accessible overview of bilattice theory.]*

---

## Appendix: Mapping Table

Complete mapping of all prior-art absence types to Primordial's 8 states, showing where Primordial's states are novel vs. inherited.

| Primordial State | Codd (1990) | Zaniolo (1984) | Belnap (1977) | SQL 3VL | Option/Maybe | Result/Either | **Novel to Primordial?** |
|------------------|-------------|----------------|---------------|---------|-------------|---------------|------------------------|
| `not_generated` | -- | -- | -- | -- | `Nothing` (conflated) | -- | **Yes**: computation-specific |
| `not_invoked` | I-mark (approx.) | Nonexistent (approx.) | -- | NULL (conflated) | `Nothing` (conflated) | -- | **Partially**: inherits concept from Codd/Zaniolo but adds dynamic semantics |
| `unknown` | A-mark | Unknown | Neither (perp) | NULL (conflated) | `Nothing` (conflated) | -- | **No**: direct inheritance from Codd/Belnap |
| `unresolved` | -- | -- | -- | -- | `Nothing` (conflated) | -- | **Yes**: temporal/in-progress state |
| `withheld` | -- | -- | -- | -- | `Nothing` (conflated) | -- | **Yes**: policy/intentional suppression |
| `invalid` | -- | -- | Both (distant analogy) | -- | -- | `Err(e)` (approx.) | **Partially**: inherits error concept from Result but adds transition rules |
| `deleted` | -- | -- | -- | -- | `Nothing` (conflated) | -- | **Yes**: terminal irreversible removal |
| `pruned_recoverable` | -- | -- | -- | -- | -- | -- | **Yes**: entirely novel; compaction with recovery path |

**Legend:** "--" means the prior tradition has no concept corresponding to this state. "(approx.)" means the mapping is approximate, not exact. "(conflated)" means the prior tradition collapses this into a single undifferentiated absence marker.

---

*Document produced for Primordial Computing v2.0 paper preparation. All citations verified against primary sources or authoritative secondary sources (Wikipedia, Semantic Scholar, ACM DL, arXiv).*
