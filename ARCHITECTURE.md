# Architecture Decisions

## Why Kafka is partitioned by user_id

Kafka guarantees message ordering within a partition, not across partitions. By partitioning on `user_id`, all feature updates for a given user are routed to the same partition and consumed in the exact order they were produced. This is the ordering guarantee that materialization depends on.

If messages were partitioned randomly or by topic, two updates for the same user could land on different partitions and be consumed by different workers at different speeds. A newer update might be processed first, and then a stale update arrives and overwrites it in Redis. The online store would serve an older value with no indication that anything went wrong. This is not a theoretical concern — it happens under load whenever consumer lag varies across partitions.

Partitioning by `user_id` eliminates this class of bug entirely. The tradeoff is that a single high-volume user's updates are serialized through one partition, but for a recommendation feature set where updates arrive at human-interaction rates, this is not a bottleneck.

## Why Delta Lake is written first in the dual-write

Delta Lake is the source of truth. The write order — Delta first, Redis second — is chosen so that every failure mode has a recovery path.

If Delta succeeds and Redis fails, the record exists in the durable offline store. The scheduled parity check will detect the missing Redis entry and flag it as a violation. The recovery path is straightforward: replay the record from Delta into Redis. The inconsistency is temporary and self-healing.

If the order were reversed — Redis first, then Delta — a Delta failure would leave a value in the online store with no durable backing. Redis is serving a record that does not exist in the offline store. There is no parity check that can fix this, because the source of truth never received the write. The only options are to silently serve unbacked data or to delete the Redis entry and lose the update entirely. Neither is acceptable.

Delta-first means the worst case is a temporary gap in the online store. Redis-first means the worst case is a silent consistency violation with no recovery path. The choice is obvious.

## Why parity validation is scheduled, not inline

An inline parity check on every write would read back the value from both Delta Lake and Redis, compare them, and block the write's response until the comparison completes. This doubles the critical path latency by adding a read from each store to every write operation. Worse, it couples the write path's availability to the read path's availability — if Redis is slow or temporarily unreachable during the read-back, the write fails even though both stores accepted the data.

The scheduled approach decouples writes from validation entirely. Writes are fast: validate, write Delta, write Redis, return. Parity runs in the background on a configurable interval, comparing all shared entities between the offline and online stores. The 0.001 absolute tolerance per feature absorbs normal floating-point serialization noise across Delta Lake's Parquet encoding and Redis's string representation. The 0.1% entity threshold means a handful of rounding artifacts do not trigger a false alarm, but systemic drift — a broken writer, a schema mismatch, a failed Redis replay — is caught and flagged.

The tradeoff is detection latency. A partial write failure is not caught until the next parity run. For a recommendation feature store where features represent aggregated user behavior over days or weeks, minutes of detection latency are acceptable. For a system where millisecond-level consistency matters, a different architecture would be required.

## What happens on a partial write failure

There are exactly two failure modes in the dual-write path, and both are handled explicitly.

If Delta Lake fails before the Redis write executes, the exception propagates immediately to the caller. Redis is never written. The record does not exist in either store, so there is no inconsistency. The system is in the same state it was in before the write was attempted. The producer receives the error and can retry the write without risk of duplication or divergence.

If Delta Lake succeeds but the subsequent Redis write fails, the exception still propagates to the caller. The record now exists in Delta but not in Redis. This is a temporary inconsistency: the offline store has a value that the online store does not. The caller knows the write partially failed and can retry, which will append a duplicate to Delta (acceptable for an append-only store) and succeed in Redis. Even without a retry, the scheduled parity check will detect the missing Redis entry on its next run and flag the user as a violation. The recovery path is to replay the Delta record into Redis, restoring consistency without data loss.

The design never silently swallows a partial failure. The caller always receives the exception. The parity check always detects the divergence. There is no state where one store has data the other lacks without either the caller or the background validator knowing about it.
