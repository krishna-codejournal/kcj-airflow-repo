# Apache Airflow: Core Concepts

> A structured guide to the fundamental building blocks of Apache Airflow.

---

## Overview

Apache Airflow is a platform for programmatically authoring, scheduling, and monitoring workflows. Understanding its core concepts is essential before building your first pipeline. This document covers the four foundational concepts: **DAG**, **Operator**, **Task & Task Instance**, and **Workflow**.

---

## 1. DAG (Directed Acyclic Graph)

The DAG is the most important concept in Airflow. It is a **collection of all the tasks you want to run**, organized in a way that reflects their relationships and dependencies.

A DAG defines the **structure** of your entire workflow — it shows which tasks must complete before others can begin.

### Analogy
Think of a DAG like a **recipe**. Just as a recipe lists all the steps to make a dish in the correct order, a DAG lists all the tasks to complete your data workflow in the right sequence.

### What Makes a Valid DAG?

| Property | Explanation |
|---|---|
| **Directed** | Dependencies flow in one direction (Task A → Task B) |
| **Acyclic** | No cycles or loops are allowed |
| **Graph** | Tasks are nodes; dependencies are edges |

### Example

```
T1 ──┐
T2 ──┼──► T4   ✅ Valid DAG (T4 depends on T1, T2, T3)
T3 ──┘
```

```
T1 ──► T4
▲       │
└───────┘         ❌ Invalid — T1 depends on T4, and T4 depends on T1 (cycle!)
```

> **Key Rule:** If you have a loop in your graph, it is **not** a DAG. The "acyclic" part means zero cycles, ever.

---

## 2. Operator

An operator defines a **single, ideally idempotent task** in your DAG.

- **Idempotent** means: running the task multiple times with the same input always produces the same output, regardless of when it runs.
- Operators allow you to break down your workflow into discrete, manageable units of work.

### Analogy
If a DAG is like a recipe, operators are like the **individual instructions** in that recipe. For example, "break five eggs" is one step — similarly, an `ExtractDataOperator` is one task that pulls data from a specific source.

### Common Built-in Operators

| Operator | Purpose |
|---|---|
| `PythonOperator` | Execute a Python function or script |
| `BashOperator` | Execute a Bash command or script |
| `SQLExecuteQueryOperator` | Run a SQL query against a database (e.g., MySQL, PostgreSQL) |
| `FileSensor` | **Wait** for a file to appear (a sensor, not an executor) |

### Finding Operators

Airflow has thousands of operators available through **Providers** — Python packages that add integrations with external tools and services (e.g., Airbyte, AWS, GCP, Snowflake).

Browse all available providers and their operators at the [Airflow Providers Registry](https://airflow.apache.org/docs/apache-airflow-providers/index.html).

---

## 3. Task & Task Instance

### Task
A **task** is a specific instance of an operator that has been assigned to a DAG. Once an operator is placed inside a DAG, it becomes a task. This is why the terms "operator" and "task" are often used interchangeably.

Tasks are the **actual units of work** that get executed when your DAG runs.

### Task Instance
A **task instance** represents the execution of a task at a **specific point in time**. It captures the run date, status, duration, and logs for that particular execution.

### Analogy

| Concept | Recipe Analogy |
|---|---|
| Operator | "Break five eggs" (the instruction) |
| Task | "Break five eggs" assigned to this specific recipe |
| Task Instance | "Breaking five eggs on July 1st at 2:00 PM" (the actual execution) |

---

## 4. Workflow

A **workflow** is the entire process defined by your DAG — all tasks combined with their dependencies. It represents your complete data pipeline, showing how all the pieces fit together to achieve a goal.

### Analogy
A workflow is like the **entire process of preparing a meal** — from gathering ingredients, to cooking, to serving.

### Example Workflow: Daily Sales Report

```
Extract Data ──► Process Data ──► Generate Report ──► Send Email
```

Each arrow represents a dependency. The pipeline runs left to right, and each task only begins once its predecessor has successfully completed.

---

## Summary

| Concept | Definition | Recipe Analogy |
|---|---|---|
| **DAG** | The overall workflow structure and task dependencies | The full recipe |
| **Operator** | A single, reusable task definition | One instruction in the recipe (e.g., "whisk eggs") |
| **Task** | An operator assigned to a specific DAG | That instruction as part of *this* recipe |
| **Task Instance** | The actual execution of a task at a specific time | Following that instruction at 2 PM on July 1st |
| **Workflow** | The entire process from start to finish | The complete meal preparation process |

> **Note:** In practice, the term **DAG** is used far more commonly than "workflow" in the Airflow ecosystem. Going forward, DAG and workflow can be considered synonymous.

---

*Documentation based on Apache Airflow core concepts introduction.*
