# Moved: EMR to PostgreSQL Ingestion Architecture

> Status: External design exercise / not implemented in this repo.
> Evidence boundary: The EMR, Spark, PostgreSQL, Aurora, and Airflow pipeline referenced here is not present in this repository; the analysis is a supplied design review, not a runtime-backed implementation.

This article has moved to [../01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md](../01-agent-architecture/02-emr-to-postgresql-ingestion-architecture.md).

The architecture below is the production pattern under review for lower end-to-end latency. It represents the current EMR → Spark → PostgreSQL/Aurora ingestion design described in the supplied brief, and the repository treats it as an architectural design problem rather than a code-backed runtime implementation.

The smallest high-leverage evolution is therefore not a rewrite or a tuning exercise. It is to make the existing boundaries observable and explicit: separate change detection from file publication, clarify the role of Spark versus PostgreSQL, and reduce unnecessary rows and work before they cross the EMR-to-RDS boundary.

The likely architectural opportunity is to reduce the number of rows crossing EMR to RDS. That is a hypothesis, not a measured result. Correctness depends on proving entity identity, update semantics, duplicate handling, and the exact transaction boundary for the target schema.

## 2. Current Architecture

The supplied baseline is:

```text
Airflow
  |
  v
EMR / Spark
  |
  v
Full Parquet generation
  |
  v
Full old-vs-new comparison
  |
  v
Delta Parquet
  |
  v
Spark JDBC
  |
  v
PostgreSQL / Aurora RDS
  |
  v
Dedupe / Merge
  |
  v
Primary keys / foreign keys / indexes
  |
  v
VACUUM ANALYZE
```

This is the architecture described in the supplied brief and is the design under review for optimization. The repository treats it as a production architecture pattern to reason about and improve, rather than a local runtime implementation that must be executed here.

A compact responsibility model is:

| Component | Responsibility | Evidence status |
|---|---|---|
| Airflow | Schedule jobs, express dependencies, apply retry and timeout policy | Supplied design; architecture under review |
| Source / S3 | Hold source snapshots, Parquet outputs, and possibly deltas | Supplied design; architecture under review |
| EMR / Spark | Normalize, validate, compare, deduplicate, and produce files | Supplied design; architecture under review |
| JDBC boundary | Transfer rows and create database sessions/transactions | Supplied design; architecture under review |
| PostgreSQL / Aurora | Authoritative state, constraints, indexes, and serving queries | Supplied design; architecture under review |
| Finalization | Complete schema objects and maintenance after load | Supplied design; architecture under review |

Airflow should remain an orchestration layer. Airflow's documentation describes DAGs as schedules, tasks, dependencies, callbacks, and operational details; the DAG itself does not own the internal correctness semantics of the data movement or merge logic.

## 3. Current Latency Path
The EMR / Spark / PostgreSQL ingestion architecture discussion is now classified as an agent-architecture topic rather than a production-lessons article, and the repository-specific caveat about missing implementation files is intentionally not retained in this folder.


## 17. Recommended Changes

### P0 - architectural bottleneck with strong potential evidence

**Instrument the existing boundaries.** Add stage timings, row counts, byte counts, partition counts, transaction counts, and retry outcomes. This is the highest-confidence next step because it does not change semantics and makes every later decision falsifiable.

**Separate configuration names.** Keep current values initially, but stop representing Spark compute partitions, JDBC writer partitions, transaction size, and batch size as one undifferentiated number.

### P1 - strong optimization candidate requiring benchmark

**Evaluate key/change-based delta generation.** Proceed only after proving identity, duplicate, delete, and retry semantics. Compare full-row baseline and key/signature candidate on representative snapshots.

**Evaluate the existing staging transition.** Measure stage load, delete, merge, index, and finalization separately. Replace multiple statements only if the same transaction and correctness behavior can be demonstrated.

**Evaluate targeted incremental maintenance.** Compare full-load finalization with incremental analyze/vacuum behavior using actual table statistics and query plans.

The minimum experiment should compare the current path with one candidate change at a time. Use the same source interval, schema, target snapshot, EMR release, Spark configuration, database instance, and failure policy for both runs. Capture at least three data shapes: a low-change snapshot, a high-change snapshot, and a duplicate/skew case. Do not average away correctness failures.

| Experiment | Baseline | Candidate | Required acceptance gate |
|---|---|---|---|
| Delta generation | Existing full-frame comparison | Key plus deterministic change-signature comparison | Identical insert, update, delete, and final-row results |
| JDBC boundary | Existing writer and partition calculation | Independent Spark and DB-write controls | No increase in failed tasks, duplicate effects, or invariant violations |
| Merge | Existing stage/delete/upsert sequence | One set-based transition using the same stage input | Same committed state after rerun and partial-failure recovery |
| Finalization | Existing full maintenance cycle | Targeted maintenance for incremental loads | Same query plans within an agreed tolerance and no maintenance backlog |

For each pair, record end-to-end duration and the stage metrics listed in Section 21. The candidate is not an improvement merely because one stage is faster: accept it only when the total run is no slower for the target workload, correctness is equivalent, and operational failure behavior is no worse. A candidate that wins only on a synthetic low-change case should remain an experiment result, not become the default.

Stop the experiment and retain the baseline when any of these occur: row-level results diverge, a retry is not idempotent, deletes cannot be distinguished from missing data, referential integrity changes, database lock or error rates increase materially, or the measurement does not isolate the proposed change.

### P2 - useful cleanup / simplification

**Remove actions that exist only for unconsumed counts.** Confirm audit requirements first.

**Reuse expensive DataFrames only when reused.** Persist only when the event log shows repeated recomputation and storage cost is acceptable.

**Remove redundant indexes or DDL only after inventory and query-plan review.** Indexes supporting constraints are not cleanup candidates.

### P3 - future architecture investigation

**Investigate CDC or a durable change feed.** Do not implement until upstream evidence exists.

**Consider a different ingestion mechanism.** Evaluate `COPY` or a dedicated loader only after measuring JDBC overhead and preserving transaction behavior. Do not add a microservice or messaging system by default.

## 18. Changes Actually Implemented

No EMR, Spark, Airflow, JDBC, PostgreSQL, or RDS implementation changes were made because the referenced pipeline is absent from this repository. This article adds analysis and a validation plan; it does not pretend to optimize code that is not present.

The repository's existing executable implementation is an unrelated adaptive-response delivery reference slice. It has no database or data-ingestion dependency and should not be modified to simulate this pipeline.

## 19. Validation Results

Repository validation for this article consists of source inspection and external documentation review:

- The requested pipeline filenames were searched and not found.
- No runtime benchmark was run because no pipeline implementation or data fixture exists.
- No Spark event log, Airflow run history, JDBC trace, PostgreSQL query plan, or RDS metric was available.
- No Mermaid diagram was created or modified.

Therefore this article reports architectural hypotheses and validation requirements, not performance improvements.

## 20. Remaining Unknowns

- Actual Airflow DAG topology, retries, timeouts, pools, and backfill behavior.
- Source snapshot size, change ratio, skew, duplicate rate, and schema evolution.
- Stable identity and update/delete semantics.
- Whether old target state is read by Spark, obtained from S3, or inferred another way.
- Exact use of `distinct()`, `count()`, `left_anti`, `subtract()`, `join()`, `repartition()`, and persistence.
- Exact Spark and EMR versions.
- Parquet file counts, sizes, partition columns, and S3 layout.
- JDBC driver version, writer options, isolation level, and retry behavior.
- PostgreSQL/Aurora engine version, schema, constraints, indexes, and triggers.
- Staging table lifecycle and transaction scope.
- Whether deletes are explicit or inferred by snapshot absence.
- Whether finalization is run after every incremental load.
- Autovacuum configuration and table statistics.
- Production failure rate, lock waits, connection pressure, WAL volume, and query latency.

## 21. Production Metrics Required

Before making a latency claim, capture at least:

### Airflow and orchestration

- task queue time;
- task runtime and retry count;
- executor slot and pool wait time;
- EMR startup and teardown time;
- data interval and backfill overlap.

### Spark and S3

- input and output rows and bytes;
- stage duration;
- scan duration;
- shuffle read/write bytes and time;
- spill bytes;
- task skew and stragglers;
- partition counts before and after repartition/coalesce;
- S3 read/write duration and file counts;
- number of actions and recomputation visible in the event log.

### JDBC and database

- JDBC preparation and transfer duration;
- rows per batch and transaction;
- concurrent connections;
- commit duration and failure rate;
- rows inserted, updated, deleted, and rejected;
- PostgreSQL CPU, memory, I/O, network throughput, and write latency;
- lock waits, deadlocks, active sessions, and connection saturation;
- WAL volume and checkpoint pressure;
- staging, merge, delete, index, vacuum, and analyze durations;
- query plans and row estimates for merge statements;
- dead tuples, table size, index size, and autovacuum activity.

A recommendation to increase RDS capacity, IOPS, connections, or memory requires these metrics. None is justified by this repository alone.

## 22. Files Modified

- `03-production-lessons/02-emr-spark-postgresql-ingestion-optimization.md` — added this research article.

No pipeline source files were modified because none exist in the repository.

## 23. Rollback Considerations

The article is additive and has no runtime effect. Rolling it back means deleting the article file or reverting the commit that adds it.

Any future implementation should be introduced behind an explicit baseline and a reversible flag or separate task path. Preserve the existing full-snapshot path until row-level equivalence, transaction behavior, retry idempotency, and operational metrics demonstrate that the candidate path is safe. Do not delete the baseline until rollback has been tested against representative inserts, updates, deletes, duplicate keys, nulls, partial failures, and reruns.

## Further Reading

- [Apache Spark JDBC data source](https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html) — JDBC partitioning, concurrent connections, batch size, and write options.
- [Apache Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html) — caching, shuffle partitions, join strategies, statistics, and adaptive query execution.
- [Amazon EMR Spark guide](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark.html) — Spark on EMR and S3 access context.
- [Apache Airflow DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html) — schedules, dependencies, retries, and orchestration boundaries.
- [PostgreSQL INSERT](https://www.postgresql.org/docs/current/sql-insert.html) — `ON CONFLICT` and atomic upsert semantics.
- [PostgreSQL COPY](https://www.postgresql.org/docs/current/sql-copy.html) — bulk loading behavior and failure considerations.
- [PostgreSQL routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html) — dead-row cleanup, statistics, visibility, and transaction-ID safety.
- [PostgreSQL indexes](https://www.postgresql.org/docs/current/indexes.html) — lookup benefits and write/storage overhead.
