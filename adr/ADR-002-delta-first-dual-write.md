# ADR-002: Write to Delta Lake Before Redis in Dual-Write

## Status

Accepted

## Context

The feature store maintains two copies of every feature record: Delta Lake as the durable offline store and Redis as the low-latency online store. Both writes can fail independently. A write to one store that is not followed by a write to the other creates an inconsistency. The system needs a failure strategy where every failure mode has a defined recovery path.

There are two possible orderings: write Delta first then Redis, or write Redis first then Delta. The choice determines which failure modes are recoverable and which are not.

## Decision

Delta Lake is written first. If the Delta write succeeds, Redis is written second. If either write fails, the exception propagates to the caller.

Delta is the durable source of truth. If Delta succeeds and Redis fails, the record exists in the offline store and is missing from the online store. This is a detectable, recoverable state: the scheduled parity check will flag the missing Redis entry, and the record can be replayed from Delta into Redis.

If the order were reversed and Redis were written first, a subsequent Delta failure would leave a value in the online store with no durable backing. The parity check cannot fix this because the source of truth never received the write. There is no replay path, no recovery mechanism, and no way to distinguish this state from a legitimate write without external bookkeeping.

## Consequences

Delta Lake is the authoritative record for all feature data. Redis is an eventually consistent projection of Delta, optimized for read latency. Under normal operation both stores are consistent. Under partial failure, the inconsistency is always in the same direction (Delta has data that Redis lacks, never the reverse), and recovery is always the same operation (replay from Delta to Redis).

The tradeoff is that a Delta success followed by a Redis failure leaves a temporary gap in the online store. Features for that user will be missing or stale in Redis until the next parity run or a successful retry. For a recommendation system where features represent aggregated behavior over days, a few minutes of staleness is acceptable.
