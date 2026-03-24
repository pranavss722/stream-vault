# ADR-001: Partition Kafka Topics by user_id

## Status

Accepted

## Context

Feature updates for a given user arrive as individual messages on a Kafka topic. If these messages are distributed across partitions using round-robin or hash-by-topic partitioning, two updates for the same user can land on different partitions. Different consumers process different partitions at different rates. Under load, a newer update can be consumed and written to Redis before an older update arrives on a slower partition. The older update then overwrites the newer value, and the online store silently serves stale data with no error and no indication that anything went wrong.

Kafka guarantees message ordering within a single partition. It makes no ordering guarantee across partitions. Any partitioning strategy that does not pin a user's messages to a single partition forfeits the ordering guarantee that materialization depends on.

## Decision

All feature update messages are partitioned by `user_id` (the entity key). The Kafka producer sets the partition key to the `user_id` field, ensuring that every update for a given user is routed to the same partition and consumed in the exact order it was produced.

## Consequences

Materialization can rely on strict per-user ordering. When a consumer reads messages from a partition, it processes each user's updates sequentially, so newer values always overwrite older ones. This eliminates the stale-overwrite class of bugs entirely.

The tradeoff is partition skew. If a small number of users generate a disproportionate share of updates, their partition will carry more load than others. For a recommendation feature set where updates arrive at human-interaction rates (clicks, sessions, watch events), this skew does not produce a meaningful bottleneck. If the system were later adapted for machine-generated events at thousands of updates per second per entity, the partitioning strategy would need to be revisited.
