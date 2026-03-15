# Methodology — Draft v0

## Objective

Evaluate whether typed absence, explicit provenance, and recoverable compaction improve the structural reliability of long-horizon agentic systems.

## Experimental strategy

The project will proceed in four layers:

1. **Specification**
   - define ontology
   - define invariants
   - define transition legality

2. **Implementation**
   - instrument a reference runtime with the protocol
   - encode artifacts, refs, validation, and compaction behavior

3. **Evaluation**
   - compare against simpler baselines
   - inject corruption/failures
   - measure recoverability and detection quality

4. **Generalization**
   - port to at least one additional runtime shape

## Baselines

At minimum compare against:
- flat/native logging
- hash-only integrity wrapper
- provenance-only wrapper
- full Primordial protocol

## Metrics

### Provenance
- provenance reachability fraction
- maximum reconstructable depth
- orphan artifact count

### Detection
- structural violations detected
- true positives
- false positives
- false negatives
- detection phase (generation, registration, compaction, replay)

### Compaction
- source-ref completeness
- reconstruction success rate
- compacted artifact grounding quality
- recovery latency

### Cost
- runtime overhead
- storage overhead
- compression ratio
- verification overhead

## Test families

### 1. Happy-path structure tests
- linear execution
- recursive execution
- compaction with valid refs

### 2. Mutation tests
- removed parent refs
- duplicate artifact IDs
- corrupted hashes
- fake source refs
- raw nulls where typed state is required

### 3. Fault injection
- exception before registration
- exception after registration
- partial write
- interrupted compaction
- timeout in subcall

### 4. Replay/recovery tests
- dereference pruned artifacts
- reconstruct ancestry after compaction
- verify tamper detection after encode/decode mutation

## Evidence standard

Claims should be backed by:
- code
- logs
- measured outputs
- reproducible test cases

Self-report from the system is not sufficient evidence.

## Near-term milestone

A serious first milestone should include:
- ontology draft
- transition validator prototype
- mutation tests
- compaction stress tests
- one baseline comparison report

## Limitations to state explicitly

- structural correctness does not guarantee semantic correctness
- ontology quality depends on correct state assignment
- compaction grounding may still omit latent semantic detail
- results from one runtime do not automatically generalize
