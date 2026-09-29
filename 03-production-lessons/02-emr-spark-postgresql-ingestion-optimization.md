# Architecture Optimization for EMR to PostgreSQL Ingestion

## 1. Executive Summary

The supplied EMR, Spark, Parquet, JDBC, and PostgreSQL ingestion pipeline is a plausible optimization target, but it is not implemented in this repository. The named files (`get_deltas_job.py`, `parquet_to_rds_job.py`, `parquet_delta_to_rds_job.py`, `get_full_ingest_schema.py`, `get_finalize_schema.py`, and `get_inferred_job.py`) are absent, as are Airflow DAGs, Spark submit scripts, SQL migrations, and runtime metrics. That means this article can establish a disciplined architecture and a validation plan, but it cannot honestly claim that the current pipeline performs a particular join, shuffle, write, delete, or merge.

The smallest high-leverage evolution is therefore not a rewrite or a tuning exercise. It is to make the existing boundaries observable and explicit: separate change detection from file publication, separate Spark partitioning from database concurrency, and define one controlled database ingestion boundary whose row counts and transaction behavior are measurable. Only after those facts are available should the system move from full-frame comparison to key/change comparison or replace staging with a different merge strategy.

The likely architectural opportunity is to reduce the number of rows crossing EMR to RDS. That is a hypothesis, not a measured result. Correctness depends on proving entity identity, update semantics, delete semantics, duplicate policy, and retry idempotency before changing the delta algorithm.

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

This is the architecture described in the supplied brief, not an architecture confirmed by repository code. The repository search found no implementation of the named jobs or any equivalent EMR-to-RDS path. The distinction matters: the article can analyze the stated design, but it must not report its costs as observations.

A compact responsibility model is:

| Component | Responsibility | Evidence status |
|---|---|---|
| Airflow | Schedule jobs, express dependencies, apply retry and timeout policy | Supplied design; no repository DAG |
| Source / S3 | Hold source snapshots, Parquet outputs, and possibly deltas | Supplied design; no repository paths |
| EMR / Spark | Normalize, validate, compare, deduplicate, and produce files | Supplied design; no Spark job |
| JDBC boundary | Transfer rows and create database sessions/transactions | Supplied design; no writer configuration |
| PostgreSQL / Aurora | Authoritative state, constraints, indexes, and serving queries | Supplied design; no schema or SQL |
| Finalization | Complete schema objects and maintenance after load | Supplied design; no finalization code |

Airflow should remain an orchestration layer. Airflow's documentation describes DAGs as schedules, tasks, dependencies, callbacks, and operational details; the DAG itself does not own the internal work performed by a task. That supports keeping Spark and PostgreSQL responsibilities in their respective execution environments rather than embedding data processing in orchestration code.

## 3. Current Latency Path

The end-to-end path implied by the brief is:

```text
T_total =
    T_Airflow_queue
  + T_EMR_startup
  + T_source_read
  + T_Spark_normalize
  + T_Spark_compare
  + T_Spark_shuffle
  + T_Parquet_write
  + T_JDBC_prepare
  + T_JDBC_transfer
  + T_DB_commit
  + T_DB_dedupe_merge
  + T_finalization
```

The important point is that `T_JDBC_transfer` is only one term. Reducing JDBC time by increasing concurrent writers can increase database contention, transaction conflicts, WAL volume, or finalization cost. The optimization target is total elapsed time subject to correctness, not the shortest individual stage.

The first measurement should produce one record per stage and table:

| Field | Purpose |
|---|---|
| `run_id` | Correlate Airflow, Spark, S3, and database events |
| `stage` | Identify the lifecycle step |
| `table` | Identify the target relation |
| `input_rows` / `output_rows` | Measure data reduction |
| `input_bytes` / `output_bytes` | Measure transfer and storage volume |
| `spark_partitions` | Describe compute layout |
| `db_write_partitions` | Describe JDBC concurrency |
| `jdbc_batch_size` | Describe rows per JDBC batch |
| `transaction_rows` | Describe commit scope |
| `start_ts` / `end_ts` / `duration_ms` | Measure stage latency |
| `status` and `attempt` | Analyze retries and partial failures |

No such telemetry exists in this repository, so no latency contribution is currently confirmed.

## 4. Architectural Bottlenecks

The following are candidates, not proven bottlenecks:

1. **Full-frame delta generation.** If old and new snapshots are repeatedly materialized, counted, deduplicated, written, and compared, the pipeline may process substantially more data than it ultimately changes.
2. **Coupled partition controls.** If `rows_per_partition`, `num_partitions`, `repartition`, and JDBC writer settings are derived from one number, Spark compute parallelism may accidentally determine RDS connection concurrency.
3. **Oversized EMR to RDS boundary.** Sending unchanged rows to RDS makes the database participate in work that could potentially have been avoided upstream.
4. **Database-side cleanup.** Staging, deduplication, delete, upsert, index maintenance, and full finalization can multiply database writes relative to the minimal state change.
5. **Repeated Spark actions.** `count()`, `distinct()`, `subtract()`, writes, and later actions can trigger repeated scans if DataFrames are not reused or persisted deliberately.

Each item requires the actual job code and a Spark event log or database trace before it becomes a confirmed finding.

## 5. Confirmed Findings

The following are confirmed by repository inspection or primary documentation:

- **The named ingestion implementation is absent.** Repository search found no `get_deltas_job.py`, `parquet_to_rds_job.py`, `parquet_delta_to_rds_job.py`, `get_full_ingest_schema.py`, `get_finalize_schema.py`, or `get_inferred_job.py`.
- **The repository does not contain an Airflow or Spark runtime.** The current project is a documentation-led repository with a small Python reference implementation for adaptive response delivery.
- **Spark separates JDBC write parallelism from ordinary Spark transformation concepts.** Spark documents `numPartitions` as the maximum number of partitions used for JDBC reading and writing and the maximum number of concurrent JDBC connections. If the number of partitions to write exceeds the limit, Spark coalesces before writing.
- **Spark's JDBC `batchsize` controls rows per insert round trip, not the number of database connections.** These are separate controls.
- **Spark shuffle partitioning is a separate concern.** `spark.sql.shuffle.partitions` configures partitions for joins and aggregations; it is not the same setting as JDBC write concurrency.
- **Spark's `repartition` and `coalesce` change DataFrame partition layout.** They do not by themselves define database transaction semantics or correctness boundaries.
- **PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` provides an atomic insert-or-update outcome when its conflict target is backed by an appropriate unique constraint or index.** It does not define application-specific delete semantics.
- **PostgreSQL `COPY FROM` invokes destination triggers and checks constraints.** It is a bulk-load mechanism, not a replacement for a state transition design.
- **PostgreSQL `VACUUM` has multiple responsibilities.** It reclaims reusable space from dead row versions, updates planner statistics when paired with `ANALYZE`, maintains visibility information, and prevents transaction ID wraparound. It should not be removed merely because it adds elapsed time.
- **PostgreSQL indexes improve lookup but add system overhead.** An index required for a primary key, foreign key support, conflict target, or serving query is not redundant merely because it costs write time.
- **Airflow tasks can retry and time out independently of the internal Spark or database implementation.** Retry behavior must therefore be designed for idempotency at the data boundary.

## 6. Inferences

The following are logical consequences of the supplied architecture, but are not measured repository facts:

- If full old and new frames are compared on every run, the amount of comparison work is driven by snapshot size rather than change size.
- If a stable entity key and deterministic change signature exist, comparing key plus signature can reduce the rows that need to cross the database boundary. This is only safe when duplicate and ordering semantics are understood.
- A `count()` followed by a write or another action can cause additional work unless the relevant DataFrame is persisted or the count is eliminated. The actual cost depends on the unprovided job plan and storage layout.
- A single partition calculation used for Spark transformations and JDBC writes couples independent resource controls. Separating them should improve operational control, but the end-to-end latency effect requires measurement.
- Staging can be valuable when it provides a transactionally inspectable input, type conversion boundary, retry isolation, or set-based SQL operation. Removing it without understanding those guarantees can weaken correctness.
- A smaller delta should reduce EMR-to-RDS bytes and database row-level work, but it may add key extraction, hashing, joins, or state management in Spark. The net result is a benchmark question.

## 7. Architecture That Can Be Simplified

The safe simplification is the boundary model, not an immediate replacement of algorithms:

```text
Airflow
  |
  +-- start and monitor one data interval
  |
  v
Spark job
  |
  +-- normalize and validate
  +-- produce one measured delta artifact
  +-- publish row and byte counts
  |
  v
Controlled ingestion boundary
  |
  +-- explicit database concurrency
  +-- explicit batch and transaction policy
  +-- explicit idempotency key
  |
  v
PostgreSQL
  |
  +-- authoritative set-based state transition
  +-- required constraints and indexes
  +-- targeted maintenance based on observed change
```

This removes ambiguity rather than adding a new service. It does not remove validation, staging, constraints, retries, or maintenance until their requirements are proven unnecessary.

## 8. Proposed Target Architecture

```text
                         +----------------+
                         |    Airflow     |
                         | schedule/retry |
                         +--------+-------+
                                  |
                                  v
                    +--------------------------+
                    | Source and S3 artifacts  |
                    | snapshot or change feed  |
                    +------------+-------------+
                                 |
                                 v
                    +--------------------------+
                    | EMR / Spark              |
                    | normalize                |
                    | validate                 |
                    | deduplicate              |
                    | detect changes           |
                    | publish minimal delta    |
                    +------------+-------------+
                                 |
                         rows + bytes + counts
                                 |
                                 v
                    +--------------------------+
                    | JDBC ingestion boundary  |
                    | DB concurrency           |
                    | transaction rows         |
                    | JDBC batch size          |
                    | retry/idempotency        |
                    +------------+-------------+
                                 |
                                 v
                    +--------------------------+
                    | PostgreSQL / Aurora      |
                    | stage when justified     |
                    | set-based state change   |
                    | constraints and indexes  |
                    +------------+-------------+
                                 |
                                 v
                    +--------------------------+
                    | Finalization             |
                    | targeted analyze/vacuum  |
                    | full-load maintenance    |
                    +--------------------------+
```

The architecture remains the same class of system. The evolution is that each boundary has one responsibility and measurable inputs and outputs.

## 9. Current vs Proposed Architecture

| Area | Current | Proposed | Why | Risk | Evidence |
|---|---|---|---|---|---|
| Delta generation | Full old-vs-new comparison is stated, but code is absent | Key/change comparison only after identity and semantics are proven | Potentially reduces comparison and transfer volume | Incorrect inserts, updates, or deletes | Requires job code and fixtures |
| Spark partitioning | Unknown; brief names `repartition` and `coalesce` | Explicit compute and shuffle settings | Prevents unrelated controls from being coupled | More configuration surface | Spark docs support separation; pipeline values absent |
| JDBC boundary | Spark writer is stated | One explicit ingestion policy | Makes connection and commit behavior reviewable | Boundary may expose driver limitations | Requires writer configuration and DB trace |
| DB concurrency | Unknown; possibly derived from partition count | Separate `db_write_partitions` / max concurrency | Avoids treating executor parallelism as DB capacity | Too few or too many connections | Requires production metrics |
| Transaction sizing | Unknown | Explicit rows or bytes per transaction | Controls rollback and lock scope | Smaller transactions may add commit overhead | Requires driver and SQL behavior |
| Delta staging | Stated as part of the flow, implementation absent | Retain if it provides validation or atomic transition; otherwise minimize | Preserves correctness while reducing unnecessary work | Removing it may break recovery or type handling | Requires SQL and failure tests |
| DB merge | Dedupe / merge is stated | Set-based transition keyed by proven identity | Avoids row-by-row application behavior | Conflict and delete semantics may differ | Requires schema and SQL |
| Finalization | PK, FK, indexes, `VACUUM ANALYZE` stated | Full-load and incremental policies separated only with evidence | Avoids repeating full maintenance unnecessarily | Stale statistics or integrity gaps | Requires workload and database metrics |
| CDC / change feed | Not present in repository | Investigate upstream only | Could avoid snapshots entirely | New source contract and replay semantics | Requires upstream evidence |

## 10. Delta Generation Redesign

### What must be established first

Before changing the algorithm, answer these questions from schema and business semantics:

1. What is the stable entity identity: one column, a compound key, or no stable key?
2. Is one row per key guaranteed, or are duplicates meaningful records?
3. Does an update mean any payload difference, selected-column difference, or a version transition?
4. Are deletes represented explicitly, inferred by absence, or unsupported?
5. Does ordering affect the target state?
6. Can two source rows for one key arrive in the same interval?
7. Is a deterministic content signature already available upstream?
8. What makes a retry safe?

Without these answers, replacing `subtract()` or `distinct()` is not an optimization; it is a semantic change.

### Candidate design

```text
Current, if the brief is literal:

old snapshot + new snapshot
          |
          +-- full-row comparisons
          +-- duplicate handling
          +-- repeated actions and writes
          v
      delta artifact

Candidate:

old key/state + new normalized key/state
          |
          +-- validate one row per identity
          +-- compare identity and change signature
          +-- classify INSERT / UPDATE / DELETE
          v
      minimal delta artifact
```

A content hash can be useful when rows are wide and equality is expensive, but it should not be introduced automatically. It must be deterministic across data types, null representations, field ordering, encoding, and schema evolution. The hash must not replace a stable key; it is a change signature, not identity.

`distinct()` is removable only if duplicates are either impossible by contract or already rejected by a validation step whose result is preserved. `subtract()` is replaceable only when its set semantics match the intended row identity and update/delete rules. A key-based anti-join or full outer join may be more precise, but it can also introduce a shuffle. Spark's optimizer and runtime statistics should be inspected rather than assuming that a named operation is always cheaper.

`count()` should be removed when it exists only for logging or partition arithmetic and does not drive a correctness decision. If counts are required for audit, collect them as part of a deliberate observability action or from a single materialized result. Persisting a DataFrame is justified only when multiple downstream actions reuse the same expensive computation; persistence has memory and storage costs and should be measured.

### Correctness invariant

**Requires validation.** A key/change redesign preserves correctness only after row-level fixtures prove the counts and values for inserts, updates, deletes, duplicate keys, nulls, missing records, retries, and schema changes.

## 11. EMR to RDS Boundary Redesign

The boundary should expose five independent controls:

| Control | Meaning | Must not be confused with |
|---|---|---|
| Spark compute partitions | Parallel units for transformations | DB connections |
| Spark shuffle partitions | Parallel units for joins and aggregations | JDBC batch size |
| JDBC write partitions | Maximum concurrent write tasks/connections | Transaction rows |
| JDBC batch size | Rows per JDBC round trip | Total transaction size |
| Transaction size | Rows or bytes committed together | Spark partition count |

Spark's JDBC documentation is explicit that `numPartitions` controls the maximum partitions and concurrent JDBC connections for reads and writes; writes above the limit are coalesced. It also documents `batchsize` separately as rows per insert round trip. This is enough to reject a common architectural mistake: deriving all of these values from `rows_per_partition` without modeling their different effects.

The controlled boundary should receive a delta artifact plus metadata:

```text
run_id
source_interval
artifact_uri
schema_version
entity_key_definition
row_count
byte_count
insert_count
update_count
delete_count
content_signature_version
idempotency_key
```

The boundary should validate the artifact before opening broad database concurrency. It should cap connections independently from Spark's executor count, fail before a partial state transition when schema or contract checks fail, and make the commit scope visible in logs.

### Correctness invariant

**Requires validation.** Separating controls should preserve data values, but transaction atomicity and retry behavior depend on the writer and merge implementation that are absent here.

## 12. JDBC / Transaction Architecture

A JDBC writer is a transport mechanism, not a complete ingestion architecture. The design must answer:

- Which rows are in one transaction?
- Can a failed task be retried without duplicating or corrupting state?
- Does a retry repeat an insert, a stage load, or an idempotent merge?
- Are multiple tasks writing the same key range concurrently?
- Which unique constraints or locks serialize conflicting rows?
- What happens if Spark reports a task failure after the database committed?
- Are database errors classified as retryable or permanent?

The initial implementation should expose configuration with neutral defaults rather than tuning values:

```text
spark_compute_partitions
spark_shuffle_partitions
db_write_partitions
jdbc_batch_size
rows_per_transaction
max_db_concurrency
```

The names are more important than the initial numbers because they make the architecture testable. Defaults should remain unchanged until a baseline exists.

For large bulk loads, PostgreSQL `COPY` may be a candidate for the staging path because it is designed to move rows in bulk and reports copied row counts. It does not automatically solve state transition semantics, conflict handling, or rollback policy. A `COPY FROM` failure can leave dead row versions that require vacuuming, so the failure behavior must be part of the design.

### Correctness invariant

**Requires validation.** The proposed separation does not change semantics by itself. Any change from JDBC inserts to `COPY`, or any change to transaction scope, requires integration tests against the actual PostgreSQL version and schema.

## 13. Delta Staging / Merge Architecture

The stated pattern is:

```text
stage rows
   |
   v
delete target rows
   |
   v
insert or upsert
   |
   v
drop staging
```

That pattern may be justified when staging provides one or more of the following:

- schema and type validation before touching the target;
- a stable input relation for a set-based operation;
- isolation between retries and the authoritative table;
- a place to deduplicate before a unique constraint is encountered;
- a transaction boundary that can be inspected or rolled back;
- support for insert, update, and delete operations in one controlled statement.

It is unnecessary when it is only a temporary copy followed by row-by-row operations that could be replaced by one set-based transition without changing semantics.

PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` is atomic for an insert-or-update decision when the conflict target and unique constraint are correct. It does not by itself express deletes caused by source absence. PostgreSQL `MERGE` can mix actions, but the choice between `MERGE`, `ON CONFLICT`, and separate statements depends on the source delta contract, triggers, foreign keys, and retry behavior.

The first safe optimization is therefore to keep staging while measuring it, then reduce statements inside the existing transaction. A possible target is:

```text
load validated delta into stage
   |
   v
one set-based state transition
   |
   +-- insert new keys
   +-- update changed keys
   +-- delete explicitly represented keys
   |
   v
commit
```

Do not implement this from the supplied brief alone. The schema and SQL are not in the repository.

### Correctness invariant

**Requires validation.** The transition must preserve referential integrity, duplicate handling, delete semantics, and retry idempotency.

## 14. PostgreSQL Responsibility

| Operation | Recommendation | Reason | Evidence status |
|---|---|---|---|
| Bulk load into staging | Keep in RDS, potentially evaluate `COPY` | RDS owns relational type and constraint checks at the boundary | Candidate; no current SQL |
| Authoritative merge | Keep in RDS | State transition and concurrency belong with authoritative state | Architectural recommendation |
| Dedupe | Move upstream only if duplicate semantics are fully equivalent | Reduces DB work, but may change which duplicate wins | Requires domain validation |
| Primary keys | Keep in RDS | Identity and uniqueness are correctness constraints | Required by target schema, absent here |
| Foreign keys | Keep in RDS | Referential integrity must be enforced at the authority | Required by target schema, absent here |
| Serving indexes | Keep in RDS | Query behavior and constraints depend on them | No index inventory exists |
| Temporary staging indexes | Reduce or defer when not needed by merge plan | They add write and build cost | Requires query plans |
| Dedupe deletes | Reduce by upstream validation or set-based SQL | Avoid repeated row work | Requires duplicate policy |
| `VACUUM` | Keep according to dead-row and wraparound needs | It is maintenance, not optional decoration | PostgreSQL documentation |
| `ANALYZE` | Keep when statistics are stale or distribution changed | Planner quality depends on statistics | Requires table statistics |
| Full rebuild DDL | Restrict to full-load lifecycle | Incremental loads should not rebuild unchanged structures | Current lifecycle absent |

The guiding rule is: Spark may compute a candidate delta; PostgreSQL remains responsible for the authoritative transition and correctness constraints.

## 15. Finalization Lifecycle

The stated finalization sequence is:

```text
dedupe
  |
  v
merge
  |
  v
primary key
  |
  v
foreign key
  |
  v
indexes
  |
  v
VACUUM ANALYZE
```

That sequence may be appropriate for a full load where constraints and indexes are intentionally delayed to reduce load-time write overhead. It is not automatically appropriate for an incremental load. Recreating or rebuilding all constraints and indexes after every delta can be unnecessary, while skipping statistics or cleanup can degrade plans and storage health.

A safer lifecycle distinction is:

```text
FULL LOAD
  validate -> bulk load -> build required structures -> analyze -> targeted vacuum

INCREMENTAL DELTA
  validate -> set-based transition -> maintain existing structures
              -> analyze affected tables when needed
              -> vacuum according to dead-row and wraparound policy
```

PostgreSQL documentation says standard `VACUUM` reclaims reusable space and supports visibility and transaction-ID maintenance; `ANALYZE` updates planner statistics. It also notes that autovacuum responds to table activity and that partitioned parents may require manual analyze. Therefore the decision to replace full `VACUUM ANALYZE` with targeted maintenance requires table statistics, dead tuple counts, partitioning details, and workload evidence.

Do not move constraints earlier or remove maintenance solely to shorten the pipeline. The maintenance schedule is part of correctness and operational safety.

### Correctness invariant

**Requires production validation.** Constraints, indexes, and maintenance can be staged differently only if query behavior, referential integrity, planner statistics, and transaction-ID safety remain intact.

## 16. CDC / Change-Feed Feasibility

The repository contains no source connector, CDC configuration, version column, `updated_at` contract, revision number, operation type, or change-feed artifact. CDC is therefore:

**REQUIRES UPSTREAM INVESTIGATION.**

The decision tree should be:

```text
Does the source provide a durable ordered change feed?
  no  -> optimize snapshot comparison and delta generation
  yes -> verify replay, retention, delete events, ordering, and idempotency
         then evaluate change-feed ingestion
```

A CDC design is not automatically better. It introduces source-capture ownership, retention and replay semantics, late or out-of-order events, schema evolution, backfill behavior, and another correctness contract. Kafka, Debezium, Flink, or another platform should not be added from this repository evidence.

The minimum upstream evidence needed is:

- stable event or revision identifier;
- insert, update, and delete operation semantics;
- ordering and lateness guarantees;
- replay and backfill capability;
- retention period;
- schema evolution behavior;
- source-side transaction boundary;
- mapping from events to target keys.

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
