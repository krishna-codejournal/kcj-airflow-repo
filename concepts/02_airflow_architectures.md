# Apache Airflow: Deployment Architectures

> A guide to the two common ways to run Airflow — single-node and multi-node — and when to use each.

---

## Overview

Airflow can be deployed in two primary architectures depending on your scale, reliability requirements, and operational complexity. This document breaks down both approaches, how the components interact in each, and guidance on which setup fits your needs.

---

## 1. Single-Node Architecture

### What Is It?

A **node** is simply a single computer or server. In a single-node architecture, **all Airflow components run on one machine**. This is the default setup you get when you install and run Airflow locally or on a single server.

### Component Breakdown

| Component | Role in Single-Node Setup |
|---|---|
| **API Server** | Serves the Airflow UI and provides REST endpoints for workers and the triggerer |
| **Scheduler** | Continuously checks for tasks ready to be triggered |
| **Executor** | Part of the scheduler; uses the **Local Executor** to run multiple tasks in parallel on the same machine |
| **Workers** | Subprocesses of the scheduler; actually execute your tasks |
| **Metadata Database** | Stores all environment metadata (task instances, DAG runs, users, etc.) — typically PostgreSQL |
| **DAG File Processor** | Parses and serializes DAG Python files (from a `dags/` folder or Git repo) into the metadata database |
| **Triggerer** | Handles deferrable operators (tasks waiting on external events); only relevant if you use deferrable operators |

### How Components Communicate

A key security and scalability principle in Airflow: **workers and the triggerer never communicate directly with the metadata database**. All communication is routed through the API server.

```
┌─────────────────────────────────────────────────────┐
│                  Single Node (1 Machine)            │
│                                                     │
│   DAG File Processor ──────────────────────────┐   │
│                                                 ▼   │
│   Scheduler (+ Local Executor)         Metadata DB  │
│         │                                   ▲       │
│         ▼                                   │       │
│      Workers ──────► API Server ────────────┘       │
│      Triggerer ────►                                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Communication flow:**
- Workers and the Triggerer → communicate with the **API Server**
- API Server → communicates with the **Metadata Database**
- Scheduler → communicates directly with the **Metadata Database**
- DAG File Processor → serializes DAGs into the **Metadata Database**

### When to Use Single-Node

✅ **Good for:**
- Getting started with Airflow
- Development and testing environments
- Smaller or less complex workflows
- Teams that want a simple, easy-to-manage setup

❌ **Not ideal for:**
- High volumes of tasks
- Workflows requiring strong fault tolerance
- Production environments demanding scalability

---

## 2. Multi-Node Architecture

### What Is It?

Multi-node means running Airflow **across multiple computers or servers**. This is the standard production setup used when you need performance, scalability, and reliability at scale.

### Component Breakdown

| Component | Role in Multi-Node Setup |
|---|---|
| **API Servers** | Multiple instances behind a load balancer — provides UI access and API endpoints; if one goes down, others take over |
| **Load Balancer** | Distributes incoming UI and API requests across multiple API server instances |
| **Schedulers** | Multiple schedulers for redundancy — if one fails, others continue scheduling tasks |
| **Executors** | Part of each scheduler; uses the **Celery Executor** to distribute tasks across multiple worker machines |
| **DAG File Processors** | Multiple instances for parsing large numbers of DAG files in parallel |
| **Metadata Database** | Runs on a dedicated machine for security and scalability (typically PostgreSQL) |
| **Queue** | An external message queue (e.g., **RabbitMQ** or **Redis**) — receives tasks from the executor and distributes them to workers |
| **Workers** | One or more per node; pull tasks from the queue and execute them |

### How Components Communicate

```
                        ┌─────────────────────┐
                        │    Load Balancer     │
                        └────────┬────────────┘
                                 │
               ┌─────────────────┼──────────────────┐
               ▼                 ▼                  ▼
          API Server A      API Server B       API Server C
               └─────────────────┼──────────────────┘
                                 │
                                 ▼
                          Metadata Database
                          (dedicated machine)
                                 ▲
               ┌─────────────────┘
               │
    Scheduler A (+ Celery Executor)
    Scheduler B (+ Celery Executor)
               │
               ▼
       External Queue (Redis / RabbitMQ)
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Worker D   Worker E   Worker F
    └──────────┴──────────┘
               │
               ▼
          API Server(s) ──► Metadata Database
       (update task status)
```

**Key communication rules (same as single-node):**
- Workers **never** talk directly to the metadata database — they go through the API server to update task statuses
- Schedulers communicate **directly** with the metadata database
- The external queue sits between the executor and the workers, enabling distributed task pickup

### When to Use Multi-Node

✅ **Good for:**
- Production environments with high task volumes
- Organizations requiring fault tolerance and high availability
- Complex workflows with many parallel tasks
- Teams that need to scale infrastructure independently (add more workers, schedulers, etc.)

❌ **Not ideal for:**
- Small teams or simple workflows (adds significant operational overhead)
- Getting started — the complexity is unnecessary for learning or development

### Benefits of Multi-Node

**Scalability** — Add more worker nodes to handle larger workloads without redesigning the system.

**Reliability** — Redundant schedulers, API servers, and workers mean no single point of failure. If one component goes down, others take over.

**Performance** — Tasks are distributed across multiple machines, enabling far greater parallelism and throughput.

---

## Architecture Comparison

| Feature | Single-Node | Multi-Node |
|---|---|---|
| **Setup complexity** | Low | High |
| **Best environment** | Dev / Testing / Small workloads | Production / Large-scale |
| **Executor type** | Local Executor | Celery Executor (or Kubernetes) |
| **Queue** | Internal | External (Redis / RabbitMQ) |
| **Fault tolerance** | Low (single point of failure) | High (redundant components) |
| **Scalability** | Limited (one machine) | High (add nodes as needed) |
| **Number of schedulers** | One | Multiple (for redundancy) |
| **Number of API servers** | One | Multiple (behind load balancer) |

---

## Summary

Both architectures share the same core components and communication principles — the multi-node setup is essentially a scaled-out, hardened version of the single-node setup. The right choice depends on your workload size, reliability requirements, and operational capacity.

> For learning Airflow and building your first pipelines, the **single-node architecture** is the recommended starting point.

---

*Documentation based on Apache Airflow architecture overview — Airflow 3.0.*
