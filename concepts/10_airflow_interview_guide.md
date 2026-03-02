# Apache Airflow — Interview Guide

> Covers all topics: Architecture, DAGs, Operators, Sensors, XCom, Datasets, Metadata DB, and Setup

---

## Table of Contents

1. [Airflow Basics](#1-airflow-basics)
2. [Architecture & Components](#2-architecture--components)
3. [DAGs & Tasks](#3-dags--tasks)
4. [Operators](#4-operators)
5. [Sensors](#5-sensors)
6. [XCom](#6-xcom)
7. [Datasets](#7-datasets)
8. [Metadata Database](#8-metadata-database)
9. [Connections & Variables](#9-connections--variables)
10. [Logging & Debugging](#10-logging--debugging)
11. [Scenario-Based Questions](#11-scenario-based-questions)

---

## 1. Airflow Basics

---

**Q1. What is Apache Airflow?**

> Apache Airflow is an open-source **workflow orchestration platform** used to programmatically author, schedule, and monitor data pipelines. It was originally created at Airbnb in 2014 and later became an Apache top-level project. Pipelines are defined as **DAGs (Directed Acyclic Graphs)** written in pure Python.

---

**Q2. What is Airflow used for? What kind of workloads is it best suited for?**

> Airflow is best suited for **batch workloads** and **data engineering pipelines** such as ETL/ELT. It is used to:
> - Schedule and monitor data pipeline jobs
> - Orchestrate tasks across multiple systems (databases, APIs, cloud services)
> - Manage dependencies between tasks
>
> It is **not** designed for real-time or streaming workloads — tools like Apache Kafka or Apache Flink are better suited for that.

---

**Q3. What is a DAG in Airflow?**

> A **DAG (Directed Acyclic Graph)** is the core concept in Airflow. It is a Python file that defines a collection of tasks and their dependencies. Key properties:
> - **Directed** — tasks flow in one direction
> - **Acyclic** — no circular dependencies
> - **Graph** — tasks are nodes, dependencies are edges
>
> Each DAG has a unique `dag_id`, a `start_date`, and a `schedule_interval`.

---

**Q4. What is the difference between a DAG, a Task, and an Operator?**

> | Concept | Description |
> |---|---|
> | **DAG** | The entire pipeline definition — a Python file containing tasks and their dependencies |
> | **Task** | A single unit of work within a DAG |
> | **Operator** | The template/type that defines what a task does (e.g., PythonOperator, BashOperator) |
>
> In simple terms: A DAG contains Tasks, and each Task is an instance of an Operator.

---

**Q5. What is a TaskInstance and a DagRun?**

> - **TaskInstance** — A specific execution of a task at a specific `execution_date`. It has a state: `queued`, `running`, `success`, `failed`, `skipped`.
> - **DagRun** — A complete execution of a DAG. It contains all TaskInstances for that run. A DagRun can be triggered by the scheduler (on schedule), manually, or via the API.

---

**Q6. What is `catchup` in Airflow?**

> `catchup` controls whether Airflow should backfill missed DAG runs between the `start_date` and today.
>
> ```python
> with DAG(
>     dag_id="my_dag",
>     start_date=datetime(2024, 1, 1),
>     schedule_interval="@daily",
>     catchup=False   # 👈 don't backfill missed runs
> ) as dag:
>     ...
> ```
>
> - `catchup=True` (default) — Airflow will run all missed intervals from `start_date` to now
> - `catchup=False` — Only run from the current date forward
>
> Always set `catchup=False` unless you specifically need backfilling.

---

**Q7. What schedulers/intervals are available in Airflow?**

> Airflow supports both **cron expressions** and **preset shortcuts**:
>
> | Preset | Equivalent Cron | Meaning |
> |---|---|---|
> | `@once` | — | Run once only |
> | `@hourly` | `0 * * * *` | Every hour |
> | `@daily` | `0 0 * * *` | Every day at midnight |
> | `@weekly` | `0 0 * * 0` | Every Sunday |
> | `@monthly` | `0 0 1 * *` | First of the month |
> | `None` | — | Never scheduled (manual trigger only) |

---

## 2. Architecture & Components

---

**Q8. Explain the architecture of Apache Airflow.**

> Airflow follows a **distributed, modular architecture** with these core components:
>
> | Component | Role |
> |---|---|
> | **Webserver** | Flask-based UI for monitoring DAGs, logs, and managing connections |
> | **Scheduler** | Brain of Airflow — monitors DAGs, determines what to run, submits to Executor |
> | **Executor** | Defines *how* tasks are run (Local, Celery, Kubernetes) |
> | **Workers** | Actual processes that execute task logic |
> | **Metadata DB** | Central store for DAG state, run history, XComs, connections |
> | **Message Broker** | Queue between Scheduler and Workers (Redis/RabbitMQ — Celery only) |
> | **DAG Directory** | Folder where Python DAG files are stored |

---

**Q9. What is the role of the Scheduler in Airflow?**

> The Scheduler is the **brain of Airflow**. It:
> - Continuously reads DAG files from the DAG directory
> - Checks the metadata DB for what needs to run
> - Evaluates task dependencies and schedules
> - Submits ready tasks to the Executor
> - Updates task states in the metadata DB
>
> The Scheduler does **not** execute tasks — it only decides what and when to run.

---

**Q10. What is the difference between an Executor and a Worker?**

> - **Executor** — Lives inside the Scheduler process. Defines the *strategy* for how tasks are run. It does not run tasks itself.
> - **Worker** — The actual process that picks up and executes a task.
>
> Think of the Executor as a **manager** that decides where to send work, and Workers as **employees** who actually do the work.

---

**Q11. What are the different types of Executors in Airflow?**

> | Executor | Description | Use Case |
> |---|---|---|
> | **SequentialExecutor** | Runs one task at a time | Development/testing only |
> | **LocalExecutor** | Runs tasks as subprocesses on the Scheduler machine | Small production setups |
> | **CeleryExecutor** | Distributes tasks to a pool of Celery workers | Large-scale production |
> | **KubernetesExecutor** | Spins up a new pod per task | Cloud-native, dynamic scaling |

---

**Q12. What is the Metadata Database and why is PostgreSQL recommended over SQLite?**

> The **Metadata Database** is the central data store for everything Airflow tracks — DAG definitions, task states, run history, connections, variables, and XComs.
>
> **SQLite** is the default but:
> - Does not support concurrent writes
> - Can corrupt data when Scheduler and Webserver write simultaneously
> - Only suitable for local development
>
> **PostgreSQL** is recommended for production because:
> - Supports concurrent writes fully
> - Handles simultaneous Scheduler + Webserver operations safely
> - Scalable and reliable

---

**Q13. What does the Webserver do? Does it execute tasks?**

> The Webserver provides the **UI** built on Flask. It allows you to:
> - Visualize DAGs and their task dependencies
> - Monitor task and DAG run statuses
> - Trigger DAG runs manually
> - View logs
> - Manage connections, variables, and XComs
>
> The Webserver **does NOT execute tasks** — it only reads from the metadata database and displays information.

---

## 3. DAGs & Tasks

---

**Q14. How do you define task dependencies in Airflow?**

> Task dependencies are defined using the `>>` (right shift) and `<<` (left shift) operators, or using `.set_upstream()` / `.set_downstream()` methods.
>
> ```python
> # task_a runs before task_b
> task_a >> task_b
>
> # task_c runs after task_b
> task_b >> task_c
>
> # Full pipeline
> task_a >> task_b >> task_c
>
> # Multiple upstream tasks
> [task_a, task_b] >> task_c   # task_c runs after both a and b
> ```

---

**Q15. What is `execution_date` in Airflow?**

> `execution_date` is the **logical date** of a DAG run — it represents the start of the scheduled interval, not when the task actually ran.
>
> For example, a daily DAG scheduled on `2024-01-02` will have `execution_date = 2024-01-01` — it represents the data interval it is processing.
>
> This is important for **backfilling** and **idempotency** — tasks can use `execution_date` to know which data period to process.

---

**Q16. What is the difference between `schedule_interval` and `start_date`?**

> - **`start_date`** — The date from which Airflow should start scheduling the DAG. The first run happens after the first interval from `start_date`.
> - **`schedule_interval`** — How frequently the DAG should run (cron expression or preset like `@daily`).
>
> ```python
> with DAG(
>     start_date=datetime(2024, 1, 1),   # start from Jan 1
>     schedule_interval="@daily",         # run every day
>     catchup=False
> ) as dag:
>     ...
> # First run will be on Jan 2, with execution_date = Jan 1
> ```

---

## 4. Operators

---

**Q17. What is an Operator in Airflow?**

> An **Operator** is a template that defines a single task in a DAG. It determines what the task actually does. Each operator extends `BaseOperator` and implements an `execute()` method.
>
> Common operators:
> | Operator | Purpose |
> |---|---|
> | `PythonOperator` | Runs a Python function |
> | `BashOperator` | Runs a Bash command |
> | `SQLExecuteQueryOperator` | Runs a SQL query |
> | `EmailOperator` | Sends an email |
> | `DummyOperator` | Does nothing — used as a placeholder |

---

**Q18. What is `SQLExecuteQueryOperator` and when do you use it?**

> `SQLExecuteQueryOperator` is used to **execute SQL queries** against a database. It is provided by the `apache-airflow-providers-common-sql` package.
>
> ```python
> from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
>
> create_table = SQLExecuteQueryOperator(
>     task_id="create_table",
>     conn_id="postgres",        # Airflow connection ID
>     sql="""
>     CREATE TABLE IF NOT EXISTS users (
>         id INT PRIMARY KEY,
>         firstname VARCHAR(255)
>     )
>     """
> )
> ```
>
> The `conn_id` must match a connection defined in **Admin → Connections** in the Airflow UI.

---

**Q19. What is the difference between `PythonOperator` and a Sensor?**

> | Feature | PythonOperator | Sensor |
> |---|---|---|
> | Purpose | Execute a Python function once | Wait for a condition to be True |
> | Core method | `execute()` — runs once | `poke()` — runs repeatedly |
> | Returns | Any value | `True` or `False` |
> | Polling | No | Yes — retries until True |
> | Base class | `BaseOperator` | `BaseSensorOperator` |

---

## 5. Sensors

---

**Q20. What is a Sensor in Airflow?**

> A **Sensor** is a special type of Operator that **waits for a condition to be met** before allowing downstream tasks to run. It acts as a gatekeeper — repeatedly calling `poke()` at a defined interval until the condition is `True`.
>
> Common use cases:
> - Wait for a file to appear (FileSensor)
> - Wait for an API to become available (HttpSensor)
> - Wait for a database record to exist (SqlSensor)
> - Wait for another DAG to finish (ExternalTaskSensor)

---

**Q21. What is the `poke()` method in a Sensor?**

> `poke()` is the **core method** of every sensor. It is called repeatedly by Airflow at each `poke_interval` until it returns `True`.
>
> ```python
> def poke(self, context) -> bool:
>     condition_met = check_something()
>     return condition_met  # True = done, False = retry
> ```
>
> - Returns `True` → sensor succeeds, downstream tasks run
> - Returns `False` → wait `poke_interval` seconds, then call `poke()` again
> - Raises Exception → sensor fails immediately

---

**Q22. What is `context` in the `poke()` method?**

> `context` is a **Python dictionary** that Airflow passes to `poke()` containing all information about the current task run:
>
> ```python
> def poke(self, context) -> bool:
>     ti             = context["task_instance"]  # TaskInstance object
>     execution_date = context["ds"]             # "2024-01-01"
>     dag_id         = context["dag"].dag_id     # "my_dag"
>     return True
> ```
>
> The most important key is `context["task_instance"]` which gives access to XCom push/pull.

---

**Q23. Why does `poke()` use `context["task_instance"]` while PythonOperator uses `ti` directly?**

> In a `PythonOperator`, Airflow **inspects the function's parameter names** and automatically injects matching context variables:
> ```python
> def my_task(ti, ds):   # Airflow injects 'ti' and 'ds' by name
>     pass
> ```
>
> In a Sensor's `poke()`, it's a **class method** so Airflow passes the entire context dictionary:
> ```python
> def poke(self, context):
>     ti = context["task_instance"]  # must extract manually
> ```

---

**Q24. What are the two Sensor modes? When do you use each?**

> | Mode | Behavior | Best For |
> |---|---|---|
> | `poke` (default) | Holds worker slot the entire time | Short waits (< 5 minutes) |
> | `reschedule` | Releases worker slot between pokes | Long waits (> 5 minutes) |
>
> Always prefer `reschedule` for long-running sensors to avoid exhausting worker slots:
> ```python
> my_sensor = MySensor(
>     task_id="my_sensor",
>     mode="reschedule",   # releases slot between pokes
>     poke_interval=300,
>     timeout=86400
> )
> ```

---

**Q25. What is `soft_fail` in a Sensor?**

> `soft_fail=True` causes the sensor to be **marked as SKIPPED** instead of FAILED when it times out. This is useful for optional conditions where a timeout shouldn't fail the entire DAG.
>
> ```python
> my_sensor = MySensor(
>     task_id="optional_check",
>     timeout=300,
>     soft_fail=True   # skip gracefully instead of failing
> )
> ```

---

**Q26. What built-in sensors does Airflow provide?**

> | Sensor | Purpose |
> |---|---|
> | `FileSensor` | Wait for a file on the filesystem |
> | `HttpSensor` | Wait for an HTTP endpoint to return success |
> | `SqlSensor` | Wait for a SQL query to return a non-null result |
> | `S3KeySensor` | Wait for a file in S3 |
> | `ExternalTaskSensor` | Wait for a task in another DAG to complete |
> | `TimeDeltaSensor` | Wait for a fixed duration |

---

## 6. XCom

---

**Q27. What is XCom in Airflow?**

> **XCom (Cross-Communication)** is Airflow's built-in mechanism for tasks to share small pieces of data with each other. XCom data is stored in the **Airflow metadata database** and identified by a `key` and the `task_id` that pushed it.
>
> ```python
> # Push
> ti.xcom_push(key="user_id", value=42)
>
> # Pull
> user_id = ti.xcom_pull(task_ids="task_a", key="user_id")
> ```

---

**Q28. What are the three ways to push data into XCom?**

> 1. **Explicit `xcom_push()`**:
> ```python
> ti.xcom_push(key="my_key", value=my_data)
> ```
>
> 2. **Return value** (auto-pushed as `"return_value"`):
> ```python
> def my_task():
>     return {"id": 1}   # auto-pushed to XCom
> ```
>
> 3. **Via context in Sensors**:
> ```python
> def poke(self, context) -> bool:
>     context["task_instance"].xcom_push(key="data", value=result)
>     return True
> ```

---

**Q29. What is the default key when pushing via `return`?**

> When a `PythonOperator` returns a value, it is automatically pushed to XCom under the key `"return_value"`.
>
> ```python
> def my_task():
>     return {"id": 1}   # pushed as key="return_value"
>
> # Pull it without specifying key (defaults to "return_value")
> data = ti.xcom_pull(task_ids="my_task")
> ```

---

**Q30. What are the limitations of XCom?**

> - XCom is stored in the **metadata database** — not suitable for large data
> - Recommended max size: **48KB**
> - Data must be **JSON-serializable** (dict, list, str, int)
> - Not suitable for DataFrames, binary files, or DB connections
>
> For large data, store it in S3/a database and pass only the **file path or record ID** via XCom.

---

**Q31. How is XCom different in a Sensor vs a PythonOperator?**

> In a **PythonOperator**:
> ```python
> def my_task(ti):
>     ti.xcom_push(key="data", value=result)   # use ti directly
> ```
>
> In a **Sensor's poke()**:
> ```python
> def poke(self, context):
>     context["task_instance"].xcom_push(key="data", value=result)  # use context
> ```
>
> The difference is because `poke()` is a class method and receives the full `context` dict, not `ti` directly.

---

**Q32. Can you pull XCom from multiple tasks at once?**

> Yes, you can pull from multiple tasks individually:
> ```python
> def combine(ti):
>     result_a = ti.xcom_pull(task_ids="task_a", key="result_a")
>     result_b = ti.xcom_pull(task_ids="task_b", key="result_b")
>     total = result_a + result_b
> ```

---

## 7. Datasets

---

**Q33. What are Datasets in Airflow and when were they introduced?**

> **Datasets** were introduced in **Airflow 2.4**. They provide **data-driven scheduling** — triggering DAGs based on when data is updated rather than on a time-based schedule.
>
> A Dataset is a logical URI representing a data asset:
> ```python
> from airflow.datasets import Dataset
> my_dataset = Dataset("s3://my-bucket/orders.csv")
> ```

---

**Q34. What is the difference between a Producer DAG and a Consumer DAG?**

> - **Producer DAG** — A task that updates a dataset using the `outlets` parameter:
> ```python
> PythonOperator(
>     task_id="process_orders",
>     python_callable=process_orders,
>     outlets=[orders_dataset]   # marks dataset as updated
> )
> ```
>
> - **Consumer DAG** — A DAG that is triggered when a dataset is updated:
> ```python
> with DAG("consumer_dag", schedule=[orders_dataset]) as dag:
>     ...
> ```

---

**Q35. What logic does Airflow use when a DAG depends on multiple datasets?**

> Airflow uses **AND logic** — the consumer DAG only triggers when **all** listed datasets have been updated at least once since the last run.
>
> ```python
> with DAG(
>     "downstream_dag",
>     schedule=[dataset_a, dataset_b]  # both must be updated
> ) as dag:
>     ...
> ```

---

**Q36. How do Datasets compare to ExternalTaskSensor and TriggerDagRunOperator?**

> | Approach | Coupling | Mechanism |
> |---|---|---|
> | Time schedule | None (but fragile) | Cron/interval |
> | `ExternalTaskSensor` | Tight — knows DAG/task name | Polls for task state |
> | `TriggerDagRunOperator` | Tight — producer calls consumer | Explicit trigger |
> | **Datasets** | **Loose — URI contract only** | **Event-driven on data** |
>
> Datasets are preferred when you want to **decouple pipelines** and model true data dependencies.

---

## 8. Metadata Database

---

**Q37. Why should you switch from SQLite to PostgreSQL for Airflow's metadata DB?**

> SQLite is the default but only suitable for development:
> - Does **not support concurrent writes**
> - The Scheduler and Webserver writing simultaneously can **corrupt the database**
>
> PostgreSQL is recommended for production:
> - Fully supports concurrent writes
> - Reliable and scalable
> - Required when using CeleryExecutor (multiple workers)

---

**Q38. How do you change the metadata database in Airflow?**

> Update the `sql_alchemy_conn` in `airflow.cfg`:
>
> ```ini
> sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db
> ```
>
> Then re-initialize:
> ```bash
> airflow db init
> ```

---

**Q39. What does `airflow db init` do?**

> `airflow db init` creates all the necessary tables in the metadata database and generates the `airflow.cfg` config file. It should be run:
> - When setting up Airflow for the first time
> - After changing the `sql_alchemy_conn` to a new database

---

**Q40. What tables exist in the Airflow metadata database?**

> Key tables include:
>
> | Table | Description |
> |---|---|
> | `dag` | All registered DAGs |
> | `dag_run` | History of DAG executions |
> | `task_instance` | History of individual task runs |
> | `connection` | Stored connections |
> | `variable` | Stored variables |
> | `ab_user` | Airflow UI users |
> | `xcom` | XCom data shared between tasks |
> | `log` | Audit logs |

---

## 9. Connections & Variables

---

**Q41. What is a Connection in Airflow?**

> A **Connection** stores credentials and config for external systems (databases, APIs, cloud services). It is stored in the metadata DB and referenced in tasks by a `conn_id`.
>
> ```python
> SQLExecuteQueryOperator(
>     task_id="query",
>     conn_id="postgres",   # references the connection named "postgres"
>     sql="SELECT 1"
> )
> ```
>
> Connections can be managed via **Admin → Connections** in the UI or via the CLI:
> ```bash
> airflow connections add 'postgres' \
>   --conn-type 'postgres' \
>   --conn-host 'localhost' \
>   --conn-login 'user' \
>   --conn-password 'pass' \
>   --conn-schema 'mydb' \
>   --conn-port '5432'
> ```

---

**Q42. Why would a connection type (e.g., Postgres) not appear in the Airflow UI dropdown?**

> Connection types are provided by **provider packages**. If the provider is not installed, the connection type won't appear.
>
> Fix — install the provider:
> ```bash
> pip install "apache-airflow-providers-postgres==5.14.0" \
>   --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
> ```
> Then restart the Webserver and Scheduler.

---

**Q43. What is the difference between a Connection and a Variable in Airflow?**

> | | Connection | Variable |
> |---|---|---|
> | Purpose | Store credentials for external systems | Store config values used in DAGs |
> | Contains | Host, port, login, password, schema | Key-value pairs |
> | Access in DAG | Via `conn_id` in operators | Via `Variable.get("key")` |
> | UI Location | Admin → Connections | Admin → Variables |

---

## 10. Logging & Debugging

---

**Q44. How do you add logging in an Airflow DAG?**

> Always use Python's standard `logging` module — not `print()`. Airflow integrates it into the task log viewer:
>
> ```python
> import logging
> log = logging.getLogger(__name__)
>
> def my_task():
>     log.info("Task started")
>     log.warning("Something unexpected")
>     log.error("Something failed")
> ```

---

**Q45. What are the logging levels and when do you use each?**

> | Level | Method | Use For |
> |---|---|---|
> | DEBUG | `log.debug()` | Detailed dev info, variable values |
> | INFO | `log.info()` | Normal flow, task progress |
> | WARNING | `log.warning()` | Unexpected but non-breaking issues |
> | ERROR | `log.error()` | Failures needing attention |
> | CRITICAL | `log.critical()` | Severe failures |

---

**Q46. How do you test a single task without running the full DAG?**

> Use the `airflow tasks test` command:
> ```bash
> airflow tasks test <dag_id> <task_id> <execution_date>
>
> # Example
> airflow tasks test user_processing create_table 2024-01-01
> ```
>
> This runs the task in isolation, bypassing dependencies and not updating the metadata DB state — great for debugging.

---

**Q47. How do you check if your Airflow metadata DB connection is healthy?**

> ```bash
> airflow db check
> # Expected: Connection successful
> ```

---

## 11. Scenario-Based Questions

---

**Q48. Your DAG is showing as "Broken DAG" in the UI. What do you check?**

> 1. Check the **import errors** — the UI shows the traceback
> 2. Common causes:
>    - Missing provider package (e.g., `airflow.sdk` not found → wrong Airflow version)
>    - Syntax errors in the DAG file
>    - Missing Python dependencies
> 3. Test from CLI:
>    ```bash
>    airflow dags list  # shows broken DAGs
>    python your_dag.py  # check for import errors directly
>    ```

---

**Q49. A task fails with `The conn_id 'postgres' isn't defined`. How do you fix it?**

> The connection doesn't exist in Airflow. Fix via CLI:
> ```bash
> airflow connections add 'postgres' \
>   --conn-type 'postgres' \
>   --conn-host 'localhost' \
>   --conn-login 'airflow_user' \
>   --conn-password 'airflow_pass' \
>   --conn-schema 'mydb' \
>   --conn-port '5432'
> ```
> Or add it via **Admin → Connections** in the UI.

---

**Q50. A task fails with `permission denied for schema public`. What is the cause and fix?**

> **Cause:** The database user doesn't have permission to create tables in the `public` schema.
>
> **Fix** — grant permissions in PostgreSQL:
> ```sql
> GRANT ALL ON SCHEMA public TO airflow_user;
> GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
> ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
> ```

---

**Q51. Your sensor is running for hours and blocking other tasks. How do you fix it?**

> Switch from `poke` mode to `reschedule` mode:
> ```python
> my_sensor = MySensor(
>     task_id="my_sensor",
>     mode="reschedule",   # releases worker slot between pokes
>     poke_interval=300,
>     timeout=86400
> )
> ```
> In `poke` mode, the sensor holds a worker slot the entire time, starving other tasks.

---

**Q52. How would you pass data from a Sensor to a PythonOperator?**

> Use XCom — push in the sensor's `poke()` and pull in the PythonOperator:
>
> ```python
> # In Sensor
> def poke(self, context) -> bool:
>     data = fetch_data()
>     if data:
>         context["task_instance"].xcom_push(key="result", value=data)
>         return True
>     return False
>
> # In PythonOperator
> def my_task(ti):
>     data = ti.xcom_pull(task_ids="my_sensor", key="result")
>     print(data)
> ```

---

**Q53. When would you use Datasets instead of ExternalTaskSensor?**

> Use **Datasets** when:
> - You want **loose coupling** between producer and consumer DAGs
> - The trigger should be based on **data being updated**, not task completion
> - You want to avoid polling with a sensor
>
> Use **ExternalTaskSensor** when:
> - You need to wait for a **specific task state** in another DAG
> - The dependency is on task completion, not data
> - You need more fine-grained control over the wait condition

---

**Q54. How do you install Airflow providers safely without breaking the existing installation?**

> Always use the **constraint file** to pin compatible versions:
> ```bash
> pip install "apache-airflow-providers-postgres==5.14.0" \
>   --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
> ```
>
> Without constraints, pip may upgrade Airflow itself to a newer major version (e.g., 3.x) which can break everything.

---

**Q55. What is the difference between Airflow 2.x and 3.x syntax for DAG definition?**

> | Feature | Airflow 2.x | Airflow 3.x |
> |---|---|---|
> | DAG import | `from airflow import DAG` | `from airflow.sdk import dag` |
> | DAG definition | `with DAG(...) as dag:` | `@dag` decorator |
> | Task decorator | `from airflow.decorators import task` | `from airflow.sdk import task` |
> | Sensor base | `from airflow.sensors.base import BaseSensorOperator` | `from airflow.sdk.bases.sensor import PokeReturnValue` |
> | PythonOperator | `from airflow.operators.python import PythonOperator` | `from airflow.providers.standard.operators.python import PythonOperator` |
> | `start_date` | `datetime(2024, 1, 1)` object | `"2024-01-01"` string accepted |

---

*Interview Guide — Apache Airflow 2.10.4 | Covers Architecture, DAGs, Operators, Sensors, XCom, Datasets, Metadata DB, Connections, Logging*
