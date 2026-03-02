# Apache Airflow: Core Components

> A structured reference guide to the key components that power Apache Airflow.

---

## Overview

Apache Airflow is composed of several distinct components that work together to schedule, execute, and monitor your workflows. Understanding each component's role helps you deploy, troubleshoot, and scale Airflow effectively.

---

## Component Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                      Airflow Platform                   │
│                                                         │
│  DAG File        Scheduler      API Server (UI)         │
│  Processor  ───►  (Timer)  ───► (Dashboard)             │
│     │                │               │                  │
│     ▼                ▼               ▼                  │
│  Metadata       Executor        Workers                 │
│  Database      (Traffic Ctrl)   (Chefs)                 │
│  (Memory)           │               │                   │
│                     ▼               │                   │
│                   Queue  ◄──────────┘                   │
│                (Coffee Line)                            │
│                                                         │
│                  Triggerer                              │
│               (Event Watcher)                           │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Metadata Database

The metadata database is the **central memory of Airflow**. It stores all critical information about your workflows, tasks, and their states.

**What it stores:**
- Task run history and statuses (success, failed, running, etc.)
- Workflow definitions and schedules
- Users, connections, variables, and configuration

Without the metadata database, Airflow **cannot function** — it is a non-negotiable component.

**Supported databases:** PostgreSQL, MySQL, Oracle DB, and others.

### Analogy
> Just as you use a calendar to remember appointments, Airflow uses the metadata database to remember which tasks have run, when they ran, and what their results were.

---

## 2. Scheduler

The scheduler is responsible for **determining when tasks should run**. It monitors your DAGs and triggers task execution at the right time and in the correct dependency order.

**Key responsibilities:**
- Evaluating DAG schedules and triggers
- Queuing tasks when their dependencies are met
- Ensuring tasks run on time and in the right sequence

Without the scheduler, you cannot automate or schedule any workflows.

### Analogy
> The scheduler is like an alarm clock. If you set a task to run daily at 9 AM, the scheduler ensures it starts on time, every day.

---

## 3. DAG File Processor

The DAG file processor **parses DAG files** (Python scripts) and **serializes them** into the metadata database, making them available for the scheduler and executor to act on.

> **Note:** In Airflow 2.x, this was part of the scheduler. In **Airflow 3.0**, it became a **separate, standalone component** for improved scalability and security.

**Key responsibilities:**
- Continuously reading and parsing DAG Python files
- Interpreting task definitions and dependencies
- Writing structured execution plans into the metadata database

### Analogy
> The DAG file processor is like a librarian who continuously reads and catalogs recipe books — translating complex cooking instructions into an organized catalog that chefs can easily follow.

---

## 4. Executor

The executor **determines *how* and *where* tasks will run**. It is important to note that the executor does **not** directly run tasks itself — it manages and routes their execution.

**Key responsibilities:**
- Deciding whether tasks run sequentially or in parallel
- Selecting the target system for execution (local, Kubernetes, Celery, etc.)
- Optimizing task throughput and resource usage

**Common executors:**

| Executor | Use Case |
|---|---|
| `SequentialExecutor` | Simple, single-task-at-a-time (development/testing) |
| `LocalExecutor` | Parallel execution on a single machine |
| `CeleryExecutor` | Distributed execution across multiple workers |
| `KubernetesExecutor` | Runs each task in its own Kubernetes pod |

> **Note:** The executor is an internal component — you configure it but don't interact with it directly.

### Analogy
> The executor is like a traffic controller. Just as a traffic controller decides which cars go when to optimize traffic flow, the executor decides how to route your tasks to optimize performance.

---

## 5. API Server

The API server **exposes endpoints for task and workflow operations** and also **serves the Airflow web UI**. It is your primary interface for interacting with Airflow.

**Key responsibilities:**
- Providing REST API endpoints to trigger, stop, and inspect tasks
- Serving the Airflow web-based user interface
- Handling task operation requests from the executor

Without the API server, you cannot access the UI or programmatically control your workflows.

### Analogy
> The API server is like the dashboard in your car — it gives you real-time visibility into speed, fuel, and status. Similarly, the Airflow UI lets you monitor task states, start or stop workflows, and view execution logs.

---

## 6. Workers

Workers are the processes that **actually execute your tasks**. They pick up tasks from the queue and run them.

**Key responsibilities:**
- Receiving task assignments from the executor via the queue
- Executing the actual task code (Python functions, Bash scripts, SQL queries, etc.)
- Reporting task results and status back to the metadata database

Workers are the **engines** of Airflow — nothing gets done without them.

### Analogy
> If Airflow is a restaurant kitchen, workers are the chefs. They take orders (tasks) from the queue and execute them.

---

## 7. Queue

The queue is a **list of tasks waiting to be executed**. It manages the order in which tasks are picked up by workers, especially when many tasks are ready to run simultaneously.

**Key details:**
- Always present in any Airflow setup
- Can be **internal** (simple in-process queue) or **external** (e.g., RabbitMQ, Redis — used with CeleryExecutor)
- The type of queue depends on the executor configured

> **Note:** Like the executor, the queue is an internal component you configure but don't see directly.

### Analogy
> Think of a line at a busy coffee shop. The queue ensures tasks are processed in an orderly, manageable manner — no task jumps ahead unfairly.

---

## 8. Triggerer

The triggerer manages **deferrable tasks** — tasks that wait for an external event before proceeding (e.g., waiting for a file to arrive, an API response, or a sensor condition).

**Key responsibilities:**
- Monitoring external events asynchronously
- Freeing up worker slots while tasks are in a waiting state
- Resuming deferred tasks once their trigger condition is met

This allows Airflow to handle long-waiting tasks **without blocking workers**, making your infrastructure significantly more efficient.

### Analogy
> The triggerer is like a personal assistant watching your inbox for an important email. Instead of you sitting idle waiting, your assistant notifies you the moment it arrives — freeing you to focus on other work in the meantime.

---

## Summary

| Component | Role | Required? |
|---|---|---|
| **Metadata Database** | Stores all task states, workflow info, users, and config | ✅ Yes |
| **Scheduler** | Determines when tasks run and triggers execution | ✅ Yes |
| **DAG File Processor** | Parses DAG Python files into the database | ✅ Yes (Airflow 3.0+) |
| **Executor** | Decides *how* and *where* tasks run (internal) | ✅ Yes |
| **API Server** | Serves the UI and exposes REST endpoints | ✅ Yes |
| **Workers** | Actually execute your tasks | ✅ Yes |
| **Queue** | Manages the ordered list of tasks to be executed (internal) | ✅ Yes |
| **Triggerer** | Handles deferrable tasks waiting on external events | ⚡ Optional (advanced) |

### The Essentials to Remember

For a functioning Airflow setup, you need at minimum:

- **Metadata Database** — to store everything
- **Scheduler** — to trigger tasks on schedule
- **API Server** — to access the UI and manage workflows
- **Workers** — to actually run your tasks

The **executor** and **queue** are internal mechanisms that operate behind the scenes — you configure them but don't interact with them directly during normal use.

---

*Documentation based on Apache Airflow core components introduction — Airflow 3.0.*
