# ADR-003: Run Parity Validation as a Scheduled Check, Not Inline

## Status

Accepted

## Context

The dual-write to Delta Lake and Redis can diverge due to partial failures, serialization differences, or bugs in the write path. The system needs a mechanism to detect when the offline and online stores disagree. The question is whether this check runs inline on every write or as a scheduled background process.

An inline parity check would read back the written value from both stores after every write, compare them, and block the response until the comparison completes. This adds two read operations (one Delta, one Redis) to the critical path of every write. It also couples the write's success to the read path's availability: if Redis is slow or temporarily unreachable during the read-back, the write fails even though both stores accepted the data.

## Decision

Parity validation runs as a scheduled background check, decoupled from the write path. The check compares all entities present in both the offline and online stores. A per-feature absolute delta tolerance of 0.001 absorbs normal floating-point noise introduced by serialization differences between Delta Lake's Parquet encoding and Redis's string representation. Drift is flagged when more than 0.1% of checked entities exceed this tolerance within a validation window.

## Consequences

Writes are fast. The write path is validate, write Delta, write Redis, return. No read-back, no comparison, no additional round trips. Write availability is decoupled from read availability. A temporary Redis read slowdown does not affect write throughput.

Drift detection is asynchronous. A partial write failure or serialization bug is not caught until the next scheduled parity run. The detection latency is bounded by the parity schedule interval, not by the write path. For a feature store where the underlying data represents user behavior aggregated over days or weeks, detection within minutes is sufficient.

The 0.001 tolerance is a deliberate design choice. Floating-point values serialized through Parquet and then stored as Redis strings can accumulate rounding differences on the order of 1e-15 to 1e-10. The tolerance is set three orders of magnitude above this noise floor so that normal serialization artifacts never trigger a false alarm, but a genuine divergence (wrong value written, missed write, schema mismatch) is caught reliably. The 0.1% entity threshold serves a similar purpose at the aggregate level: a single entity exceeding tolerance could be a transient retry artifact, but hundreds of entities exceeding tolerance indicates a systemic problem.
