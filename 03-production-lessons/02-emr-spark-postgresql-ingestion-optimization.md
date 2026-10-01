# Architecture Optimization for EMR to PostgreSQL Ingestion

## 1. Executive Summary

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
