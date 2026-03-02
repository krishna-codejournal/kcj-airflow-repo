# Apache Airflow: How Airflow Runs Your Tasks

> A step-by-step walkthrough of the task execution lifecycle in Apache Airflow.

---

## Overview

Understanding how Airflow internally processes and executes tasks helps you debug issues, reason about task states, and design better pipelines. This document traces the full journey of a task — from a Python file in your DAGs folder all the way to a completed task instance in the metadata database.

---

## Components Involved

The following components participate in task execution (using the single-node architecture for simplicity):

| Component | Role |
|---|---|
| **DAGs Folder** | Directory where your DAG Python files are stored |
| **DAG File Processor** | Continuously scans the DAGs folder and serializes DAG files into the metadata database |
| **Metadata Database** | Stores serialized DAGs, DAG runs, task instances, and their states |
| **Scheduler** | Checks for tasks ready to run and submits them to the executor |
| **Executor** | Defines *how* and *where* tasks run; places task instances into the queue |
| **Queue** | Holds task instances waiting to be picked up by a worker |
| **Worker** | Pulls tasks from the queue and executes them |
| **API Server** | Receives state updates from workers and writes them to the metadata database |

---

## Task Execution: Step-by-Step

### Step 1 — Add a DAG File

You create a new Python file (e.g., `my_dag.py`) and place it in the **DAGs folder**.

```
DAGs Folder
  └── my_dag.py  ← newly added
```

---

### Step 2 — DAG File Processor Detects the File

The **DAG File Processor** continuously scans the DAGs folder **every 5 minutes** (by default) for new or updated DAG files. Once it detects `my_dag.py`, it **parses and serializes** the DAG definition into the **metadata database**.

This serialized representation is used by:
- The **API Server** — to display the DAG code and structure in the Airflow UI
- The **Scheduler** — to check whether any tasks are ready to run

---

### Step 3 — Scheduler Creates a DAG Run

When the scheduler determines a DAG is due to run, it creates a **DAG Run object** — an instance of the DAG for that specific execution time.

**DAG Run states:**

| State | Meaning |
|---|---|
| `queued` | Default state when the DAG run is created |
| `running` | Airflow has begun executing the DAG |
| `success` | All tasks completed successfully |
| `failed` | One or more tasks failed |

---

### Step 4 — Scheduler Creates Task Instance(s)

For each task ready to run within the DAG Run, the scheduler creates a **Task Instance object**. The initial state is `scheduled`.

The scheduler then **submits the task instance to the executor**.

---

### Step 5 — Executor Places Task in the Queue

The executor receives the task instance and places it into the **queue**. The task instance state is now `queued`.

> The queue ensures tasks are executed in the correct order. In a single-node setup this is an internal queue; in a distributed setup it is an external queue (e.g., Redis or RabbitMQ).

---

### Step 6 — Worker Picks Up the Task

The **worker** — the process that actually runs your task code — pulls the task instance from the queue. The task instance state moves to `running`.

> **Important reminder:** The executor does *not* run your tasks — it only decides how and where they should run. The worker is what executes the actual task logic.

---

### Step 7 — Task Completes; Worker Reports Back

Once the task finishes, the worker communicates the result to the **API Server**, which updates the task instance state in the **metadata database**.

- ✅ Task succeeded → state set to `success`
- ❌ Task failed → state set to `failed`

The scheduler reads this updated state from the metadata database and proceeds accordingly — either triggering downstream tasks or marking the DAG Run as complete.

---

## Full Execution Flow (Visual Summary)

```
You
 └──► Add my_dag.py to DAGs Folder
                │
                ▼ (every 5 min)
       DAG File Processor
                │  parses & serializes
                ▼
         Metadata Database ◄─────────────────────────┐
                │                                    │
                ▼                                    │
           Scheduler                           API Server
       (checks for tasks)                   (updates states)
                │                                    ▲
                │ creates DAG Run + Task Instance    │
                ▼                                    │
            Executor                            Worker
       (submits to queue)        ◄── pulls ──  (executes task)
                │                                    │
                ▼                                    │
             Queue ──────────────────────────────────┘
        (task instance waits)
```

---

## Task Instance State Lifecycle

```
(created by scheduler)     (submitted to executor)   (picked up by worker)
     scheduled        ──►        queued          ──►      running
                                                              │
                                              ┌───────────────┴───────────────┐
                                              ▼                               ▼
                                           success                          failed
```

---

## Key Rules to Remember

**The DAG File Processor parses the DAGs folder every 5 minutes by default.** Changes to your DAG files won't be reflected instantly — there is a short delay.

**The executor does not run tasks — workers do.** The executor is a routing and management layer; the worker is the execution layer.

**Workers never communicate directly with the metadata database.** All state updates go through the API Server for security and consistency.

**In a single-node architecture**, the scheduler, executor, queue, and workers all run within the same process on one machine. In a distributed setup, the queue and workers live on separate machines.

---

*Documentation based on Apache Airflow task execution lifecycle — Airflow 3.0.*
