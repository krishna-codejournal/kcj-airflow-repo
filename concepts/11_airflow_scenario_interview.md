# Apache Airflow — Scenario-Based Interview Q&A

> Real-world problem-solving questions covering architecture, debugging, performance, and design decisions.

---

## Table of Contents

1. [DAG Design & Pipeline Architecture](#1-dag-design--pipeline-architecture)
2. [Debugging & Troubleshooting](#2-debugging--troubleshooting)
3. [Sensors & Waiting Conditions](#3-sensors--waiting-conditions)
4. [XCom & Data Passing](#4-xcom--data-passing)
5. [Database & Connections](#5-database--connections)
6. [Performance & Scaling](#6-performance--scaling)
7. [Installation & Setup](#7-installation--setup)
8. [Real Errors You Will Face](#8-real-errors-you-will-face)

---

## 1. DAG Design & Pipeline Architecture

---

**Scenario 1:**
> You need to build a pipeline that fetches user data from an API, processes it, and stores it in a PostgreSQL database. The pipeline should run daily. How would you design this DAG?

**Answer:**

Break the pipeline into clear, single-responsibility tasks:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from datetime import datetime
import requests
import logging

log = logging.getLogger(__name__)

class IsApiAvailableSensor(BaseSensorOperator):
    @apply_defaults
    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url

    def poke(self, context) -> bool:
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                context["task_instance"].xcom_push(
                    key="raw_user", value=response.json()
                )
                return True
            return False
        except Exception as e:
            log.error("API check failed: %s", str(e))
            return False

def _extract_user(ti):
    raw = ti.xcom_pull(task_ids="check_api", key="raw_user")
    return {
        "id": raw["id"],
        "firstname": raw["personalInfo"]["firstName"],
        "email": raw["personalInfo"]["email"]
    }

def _load_user(ti):
    user = ti.xcom_pull(task_ids="extract_user")
    log.info("Loading user %s into DB", user["id"])
    # DB insert logic here

with DAG(
    dag_id="user_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False
) as dag:

    create_table = SQLExecuteQueryOperator(
        task_id="create_table",
        conn_id="postgres",
        sql="""
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY,
            firstname VARCHAR(255),
            email VARCHAR(255)
        )
        """
    )

    check_api = IsApiAvailableSensor(
        task_id="check_api",
        url="https://api.example.com/users",
        poke_interval=30,
        timeout=300,
        mode="reschedule"
    )

    extract_user = PythonOperator(
        task_id="extract_user",
        python_callable=_extract_user
    )

    load_user = PythonOperator(
        task_id="load_user",
        python_callable=_load_user
    )

    create_table >> check_api >> extract_user >> load_user
```

**Key design decisions:**
- Use a **Sensor** to wait for API availability before processing
- Each task has a **single responsibility** (check, extract, load)
- Use **XCom** to pass data between tasks
- Use `catchup=False` to avoid backfilling
- Use `mode="reschedule"` in sensor to avoid blocking worker slots

---

**Scenario 2:**
> You have two independent DAGs — `dag_orders` and `dag_inventory`. A third DAG `dag_report` should only run after both complete. How do you implement this?

**Answer:**

Use **Datasets** (Airflow 2.4+) for loose coupling:

```python
from airflow.datasets import Dataset

orders_dataset   = Dataset("s3://bucket/orders/done")
inventory_dataset = Dataset("s3://bucket/inventory/done")

# dag_orders — Producer
with DAG("dag_orders", schedule="@daily") as dag:
    PythonOperator(
        task_id="process_orders",
        python_callable=process_orders,
        outlets=[orders_dataset]   # marks dataset as updated
    )

# dag_inventory — Producer
with DAG("dag_inventory", schedule="@daily") as dag:
    PythonOperator(
        task_id="process_inventory",
        python_callable=process_inventory,
        outlets=[inventory_dataset]
    )

# dag_report — Consumer (triggers only when BOTH datasets updated)
with DAG(
    "dag_report",
    schedule=[orders_dataset, inventory_dataset]
) as dag:
    PythonOperator(
        task_id="generate_report",
        python_callable=generate_report
    )
```

**Why Datasets over ExternalTaskSensor?**
- Loose coupling — `dag_report` doesn't need to know DAG names
- Event-driven — triggers on data, not task completion
- No polling overhead

---

**Scenario 3:**
> Your DAG has 10 tasks but only 3 of them must run sequentially. The rest can run in parallel. How do you design this?

**Answer:**

```python
with DAG("parallel_dag", ...) as dag:

    start    = DummyOperator(task_id="start")
    end      = DummyOperator(task_id="end")

    # Sequential chain
    seq_1 = PythonOperator(task_id="seq_1", ...)
    seq_2 = PythonOperator(task_id="seq_2", ...)
    seq_3 = PythonOperator(task_id="seq_3", ...)

    # Parallel tasks
    parallel_tasks = [
        PythonOperator(task_id=f"parallel_{i}", ...)
        for i in range(7)
    ]

    # Sequential chain runs first
    start >> seq_1 >> seq_2 >> seq_3

    # Parallel tasks run concurrently after start
    start >> parallel_tasks >> end

    # Sequential chain also leads to end
    seq_3 >> end
```

---

**Scenario 4:**
> A junior developer wrote a DAG with `catchup=True` and `start_date` set to 1 year ago. What problem will this cause and how do you fix it?

**Answer:**

**Problem:** Airflow will trigger **365 daily DAG runs** (one for each missed day from start_date to today) all at once, overwhelming the workers and metadata database.

**Fix:**
```python
# Option 1 — Set catchup=False going forward
with DAG(
    start_date=datetime(2024, 1, 1),
    catchup=False   # 👈 only run from today forward
) as dag:
    ...

# Option 2 — If backfill is needed, control it explicitly
airflow dags backfill my_dag \
    --start-date 2024-01-01 \
    --end-date 2024-01-07   # limit the range
```

**Best practice:** Always set `catchup=False` unless you specifically need historical backfilling.

---

## 2. Debugging & Troubleshooting

---

**Scenario 5:**
> Your DAG appears in the UI as "Broken DAG". What steps do you take to debug it?

**Answer:**

Step-by-step debugging process:

```bash
# Step 1 — Check what the error is in the UI
# Go to DAGs list → look for red "!" icon → click to see traceback

# Step 2 — Try importing the DAG file directly
cd ~/projects/my-airflow-repo/dags
python user_processing.py
# Any import errors will show immediately

# Step 3 — List all broken DAGs via CLI
airflow dags list-import-errors

# Step 4 — Validate the DAG
airflow dags show user_processing
```

**Common causes:**
| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'airflow.sdk'` | DAG written for Airflow 3.x but running 2.x | Rewrite using 2.x syntax |
| `ModuleNotFoundError: No module named 'pandas'` | Missing dependency | `pip install pandas` |
| `SyntaxError` | Python syntax mistake | Fix the syntax |
| `ImportError` | Wrong import path | Check provider package is installed |

---

**Scenario 6:**
> A task ran successfully yesterday but fails today with no code changes. How do you investigate?

**Answer:**

```bash
# Step 1 — Check task logs in the UI
# DAGs → my_dag → click failed task → Logs tab

# Step 2 — Check if it's an external dependency
# - API down? Database unavailable? File missing?

# Step 3 — Check XCom values from upstream tasks
# Admin → XComs → filter by dag_id and execution_date

# Step 4 — Re-run just the failed task
airflow tasks test my_dag failed_task_id 2024-01-02

# Step 5 — Check DB connection
airflow db check

# Step 6 — Check if upstream task pushed expected XCom
airflow tasks test my_dag upstream_task_id 2024-01-02
```

**Things to check:**
- Was there a **data change** in the source system?
- Did an **external API** change its response format?
- Did a **database schema** change?
- Is there a **network connectivity** issue?

---

**Scenario 7:**
> A task is stuck in `queued` state and never runs. What is the likely cause?

**Answer:**

| Cause | Fix |
|---|---|
| No workers running | Start the Scheduler: `airflow scheduler` |
| All worker slots full | Increase `parallelism` in `airflow.cfg` or add more workers |
| Sensor in `poke` mode holding all slots | Switch sensor to `mode="reschedule"` |
| Executor misconfigured | Check executor setting in `airflow.cfg` |
| Task dependency not met | Check upstream tasks are in `success` state |

```bash
# Check if scheduler is running
airflow jobs check --job-type SchedulerJob

# Check current task states
airflow tasks states-for-dag-run my_dag <run_id>
```

---

**Scenario 8:**
> You need to re-run a failed task without re-running the entire DAG. How do you do it?

**Answer:**

**Via UI:**
1. Go to the DAG → click the failed task
2. Click **Clear** → select only that task
3. The task will re-queue and run again

**Via CLI:**
```bash
# Clear a specific task (re-queues it)
airflow tasks clear my_dag \
    --task-id failed_task \
    --start-date 2024-01-01 \
    --end-date 2024-01-01

# Test a task without affecting state
airflow tasks test my_dag failed_task 2024-01-01
```

---

## 3. Sensors & Waiting Conditions

---

**Scenario 9:**
> Your sensor is running for 6 hours and blocking all other tasks in the DAG. How do you fix this?

**Answer:**

The sensor is in `poke` mode, holding a worker slot the entire time.

**Fix — switch to `reschedule` mode:**

```python
# ❌ Before — blocks worker slot
my_sensor = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    mode="poke",           # holds slot for 6 hours!
    poke_interval=3600
)

# ✅ After — releases slot between pokes
my_sensor = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    mode="reschedule",     # releases slot between pokes
    poke_interval=3600,
    timeout=86400
)
```

In `reschedule` mode the worker slot is freed between pokes, allowing other tasks to use it.

---

**Scenario 10:**
> You want a sensor to wait for a file, but if the file doesn't arrive within 2 hours, the DAG should continue with default values instead of failing. How do you implement this?

**Answer:**

Use `soft_fail=True` so the sensor is **skipped** instead of failing, then handle the skip in the downstream task:

```python
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator

wait_for_file = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    poke_interval=60,
    timeout=7200,          # 2 hours
    soft_fail=True,        # skip instead of fail on timeout
    mode="reschedule"
)

def process_data(ti):
    import os
    if os.path.exists("/data/input.csv"):
        # File arrived — process it
        with open("/data/input.csv") as f:
            data = f.read()
    else:
        # File not found — use defaults
        log.warning("File not found, using default values")
        data = get_default_values()

    process(data)

process = PythonOperator(
    task_id="process_data",
    python_callable=process_data,
    trigger_rule="all_done"  # runs even if upstream was skipped
)

wait_for_file >> process
```

---

**Scenario 11:**
> You need to check if a PostgreSQL table has new records before processing. Which sensor do you use and how?

**Answer:**

Use `SqlSensor` — it succeeds when the SQL query returns a non-null/non-zero result:

```python
from airflow.providers.common.sql.sensors.sql import SqlSensor

wait_for_records = SqlSensor(
    task_id="wait_for_new_records",
    conn_id="postgres",
    sql="""
        SELECT COUNT(*)
        FROM orders
        WHERE created_at::date = '{{ ds }}'
        AND status = 'pending'
    """,
    # Sensor succeeds when COUNT(*) > 0
    poke_interval=300,    # check every 5 minutes
    timeout=86400,        # wait up to 24 hours
    mode="reschedule"
)
```

The `{{ ds }}` is a **Jinja template** that Airflow replaces with the execution date string at runtime.

---

## 4. XCom & Data Passing

---

**Scenario 12:**
> Task A fetches a list of 10,000 user records from an API and Task B needs to process them. Should you use XCom? If not, what would you use?

**Answer:**

**No — XCom is not appropriate here.** 10,000 records could easily exceed the recommended 48KB XCom limit and slow down the metadata database.

**Better approach — use intermediate storage:**

```python
def _fetch_users(ti):
    import json
    import boto3

    users = fetch_10000_users_from_api()

    # Store in S3
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket="my-bucket",
        Key=f"users/raw/{ti.execution_date.date()}.json",
        Body=json.dumps(users)
    )

    # Push only the file path via XCom
    file_path = f"s3://my-bucket/users/raw/{ti.execution_date.date()}.json"
    ti.xcom_push(key="users_file_path", value=file_path)


def _process_users(ti):
    import boto3, json

    # Pull the file path — NOT the data
    file_path = ti.xcom_pull(task_ids="fetch_users", key="users_file_path")

    # Load from S3
    s3 = boto3.client("s3")
    bucket = file_path.split("/")[2]
    key = "/".join(file_path.split("/")[3:])
    data = json.loads(s3.get_object(Bucket=bucket, Key=key)["Body"].read())

    process(data)
```

**Rule of thumb:** Use XCom for **small metadata** (IDs, file paths, status flags). Use S3/GCS/database for **actual data**.

---

**Scenario 13:**
> Task B is pulling XCom from Task A but getting `None`. How do you debug this?

**Answer:**

```python
# Step 1 — Verify Task A actually pushed to XCom
def task_a(ti):
    data = {"id": 1}
    ti.xcom_push(key="result", value=data)
    log.info("Pushed to XCom: %s", data)  # Add logging

# Step 2 — Check Admin → XComs in UI
# Filter by dag_id and execution_date to see what was pushed

# Step 3 — Verify task_ids and key match EXACTLY
def task_b(ti):
    # ❌ Wrong task_id
    data = ti.xcom_pull(task_ids="task_A", key="result")  # case mismatch!

    # ✅ Correct — must match exactly
    data = ti.xcom_pull(task_ids="task_a", key="result")

    if not data:
        raise ValueError("XCom data missing — check task_a ran successfully")

# Step 4 — Check Task A completed successfully
# If Task A failed, XCom push never happened
```

**Common causes of `None` from xcom_pull:**
- Wrong `task_ids` value (typo or case mismatch)
- Wrong `key` name
- Upstream task failed before pushing
- In a sensor: used `ti.xcom_push()` instead of `context["task_instance"].xcom_push()`

---

**Scenario 14:**
> You have 5 parallel tasks that each return a result, and a final task needs to combine all 5 results. How do you implement this?

**Answer:**

```python
def _task(task_num, ti):
    result = process_partition(task_num)
    ti.xcom_push(key=f"result_{task_num}", value=result)

def _combine(ti):
    results = [
        ti.xcom_pull(task_ids=f"task_{i}", key=f"result_{i}")
        for i in range(5)
    ]
    combined = merge_results(results)
    log.info("Combined %d results", len(results))
    return combined

with DAG("parallel_combine", ...) as dag:

    parallel_tasks = [
        PythonOperator(
            task_id=f"task_{i}",
            python_callable=_task,
            op_kwargs={"task_num": i}
        )
        for i in range(5)
    ]

    combine = PythonOperator(
        task_id="combine",
        python_callable=_combine
    )

    parallel_tasks >> combine
```

---

## 5. Database & Connections

---

**Scenario 15:**
> Your Airflow is connected to SQLite in production and you're seeing data corruption and random failures. What is the root cause and how do you fix it permanently?

**Answer:**

**Root cause:** SQLite does **not support concurrent writes**. The Airflow Scheduler and Webserver both write to the metadata DB simultaneously, causing corruption.

**Fix — migrate to PostgreSQL:**

```bash
# Step 1 — Create PostgreSQL DB
sudo -u postgres psql
```
```sql
CREATE DATABASE airflow_db;
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER DATABASE airflow_db OWNER TO airflow_user;
GRANT ALL ON SCHEMA public TO airflow_user;
```

```bash
# Step 2 — Update airflow.cfg
sed -i 's|sql_alchemy_conn = sqlite:///...|sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db|' airflow.cfg

# Step 3 — Re-initialize
airflow db init

# Step 4 — Recreate admin user
airflow users create --username admin --role Admin --email admin@example.com --password admin
```

---

**Scenario 16:**
> A developer on your team added a new Postgres connection in the UI, but another developer's environment doesn't have it. How do you make connections consistent across environments?

**Answer:**

Use **environment variables** or **Airflow's connection URI format** to define connections outside the UI:

```bash
# Option 1 — Environment variable (no UI needed)
export AIRFLOW_CONN_POSTGRES='postgresql://airflow_user:airflow_pass@localhost:5432/mydb'

# Option 2 — CLI to export and import connections
# Export from one environment
airflow connections export connections.json

# Import into another environment
airflow connections import connections.json

# Option 3 — Define in airflow.cfg [connections] section
# Option 4 — Use a secrets backend (HashiCorp Vault, AWS Secrets Manager)
```

**Best practice:** Never rely on manually created UI connections across environments. Use environment variables or a secrets backend for consistency.

---

**Scenario 17:**
> Your task is connecting to a PostgreSQL database on Windows from Airflow running in WSL. The connection keeps timing out. What do you check?

**Answer:**

```bash
# Step 1 — Get Windows host IP from WSL
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
# Use this IP in Airflow connection, NOT 'localhost'

# Step 2 — Test connectivity from WSL
psql -h <windows_ip> -U airflow_user -d airflow_db -p 5432

# Step 3 — Check PostgreSQL is listening on all interfaces (Windows)
# In postgresql.conf:
listen_addresses = '*'

# Step 4 — Check pg_hba.conf allows WSL connections (Windows)
# Add: host all all 0.0.0.0/0 md5

# Step 5 — Check Windows Firewall allows port 5432
# Run in PowerShell as Admin:
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow

# Step 6 — Restart PostgreSQL on Windows
Restart-Service postgresql*
```

---

## 6. Performance & Scaling

---

**Scenario 18:**
> Your Airflow deployment is processing 500+ DAGs and tasks are queuing up. What do you do to scale?

**Answer:**

| Problem | Solution |
|---|---|
| Too few workers | Add more Celery workers |
| Worker slots exhausted by sensors | Switch sensors to `mode="reschedule"` |
| Scheduler slow to parse DAGs | Reduce DAG file complexity, use `min_file_process_interval` |
| Too many concurrent tasks | Tune `parallelism` and `max_active_runs_per_dag` in `airflow.cfg` |
| SQLite metadata DB bottleneck | Migrate to PostgreSQL |

```ini
# airflow.cfg tuning for scale
[core]
parallelism = 64                 # max tasks running at once
max_active_tasks_per_dag = 16   # max tasks per DAG run

[scheduler]
min_file_process_interval = 30  # how often to parse DAG files (seconds)
```

---

**Scenario 19:**
> You notice your DAG takes 2 hours to complete but the tasks themselves only take 30 minutes total. What could cause the extra time?

**Answer:**

The most common causes:

| Cause | Diagnosis | Fix |
|---|---|---|
| Sensors in `poke` mode blocking workers | Check sensor mode | Switch to `reschedule` |
| Tasks waiting for worker slots | Check `parallelism` setting | Increase parallelism or add workers |
| Slow DAG file parsing | Check Scheduler logs | Simplify DAG file, reduce imports at top level |
| `poke_interval` too large on sensors | Check sensor config | Reduce `poke_interval` |
| Sequential tasks that could be parallel | Review task dependencies | Restructure with parallel branches |

---

## 7. Installation & Setup

---

**Scenario 20:**
> A new developer joins the team and runs `pip install apache-airflow-providers-postgres` without any flags. The next day, nothing works. What happened and how do you prevent it?

**Answer:**

**What happened:** `pip install apache-airflow-providers-postgres` without version pinning installed the latest provider (v6.x) which requires **Airflow 3.x**. pip automatically upgraded Airflow from 2.10.4 to 3.x, breaking all existing DAGs and configs.

**Fix:**
```bash
# Remove broken environment
deactivate
rm -rf .venv

# Recreate fresh venv
python3 -m venv .venv
source .venv/bin/activate

# Install Airflow with constraints
pip install apache-airflow==2.10.4 \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"

# Install provider with constraints (pins compatible version)
pip install "apache-airflow-providers-postgres==5.14.0" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
```

**Prevention:**
- Always use `--constraint` when installing Airflow or providers
- Pin all dependencies in a `requirements.txt`
- Use a `Makefile` or setup script so all developers install the same way

---

**Scenario 21:**
> After running `airflow webserver`, you get: `ImportError: cannot import name 'Sentinel' from 'typing_extensions'`. What is the cause and fix?

**Answer:**

**Cause:** `pydantic-core` requires `typing_extensions >= 4.13` which includes `Sentinel`, but an older version of `typing_extensions` is installed. This typically happens when Airflow 3.x dependencies are mixed with a 2.x installation.

**Fix — clean reinstall:**
```bash
deactivate
rm -rf .venv

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

pip install apache-airflow==2.10.4 \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
```

The constraint file ensures `typing_extensions` and all other packages are pinned to compatible versions.

---

**Scenario 22:**
> You installed Airflow but running `airflow webserver` gives `airflow: command not found` even though the venv is activated. How do you fix it?

**Answer:**

```bash
# Step 1 — Confirm venv is truly active
echo $VIRTUAL_ENV
# Should print path to your venv

# Step 2 — Check if airflow binary exists in venv
ls ~/.venv/bin/ | grep airflow

# Step 3 — If not found, Airflow may not have installed properly
pip show apache-airflow
# If not found, reinstall

# Step 4 — Try running via Python module
python -m airflow webserver

# Step 5 — If airflow exists but not found, fix PATH
export PATH=$PATH:$(python -c "import site; print(site.getsitepackages()[0])")/../../bin
```

---

## 8. Real Errors You Will Face

---

**Scenario 23:**
> `Broken DAG: ModuleNotFoundError: No module named 'airflow.sdk'`

**Cause and Fix:**

```
Cause: DAG file uses Airflow 3.x imports but you are running Airflow 2.x.

airflow.sdk was introduced in Airflow 3.0 — it does not exist in 2.x.
```

```python
# ❌ Airflow 3.x — won't work on 2.x
from airflow.sdk import dag, task
from airflow.sdk.bases.sensor import PokeReturnValue

# ✅ Airflow 2.x — correct imports
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.base import BaseSensorOperator
```

---

**Scenario 24:**
> `AirflowNotFoundException: The conn_id 'postgres' isn't defined`

**Cause and Fix:**

```
Cause: The connection named 'postgres' does not exist in Airflow's metadata DB.
The DAG references conn_id="postgres" but no such connection was created.
```

```bash
# Fix — create the connection via CLI
airflow connections add 'postgres' \
  --conn-type 'postgres' \
  --conn-host 'localhost' \
  --conn-login 'airflow_user' \
  --conn-password 'airflow_pass' \
  --conn-schema 'mydb' \
  --conn-port '5432'

# Verify
airflow connections get postgres
```

---

**Scenario 25:**
> `psycopg2.errors.InsufficientPrivilege: permission denied for schema public`

**Cause and Fix:**

```
Cause: The PostgreSQL user does not have permission to create tables
in the public schema of the database.
```

```sql
-- Connect to PostgreSQL and grant permissions
\c your_database_name

GRANT ALL ON SCHEMA public TO airflow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO airflow_user;
```

---

**Scenario 26:**
> `airflow tasks test` gives `Task create_table not found` even though the task exists in the DAG.

**Cause and Fix:**

```
Cause: The task_id passed to the command doesn't match the task_id defined in the DAG.
Task IDs are case-sensitive and must match exactly.
```

```bash
# ❌ Wrong task_id
airflow tasks test user_processing create_table 2024-01-01
# Error: Task create_table not found

# ✅ Check the actual task_id in your DAG file first
# Then use the exact task_id
airflow tasks test user_processing create_user_table 2024-01-01
```

---

**Scenario 27:**
> Installing a provider upgrades Airflow from 2.10.4 to 3.x automatically.

**Cause and Fix:**

```
Cause: Running pip install without --constraint allows pip to resolve
the latest compatible versions, which may require a newer Airflow version.

apache-airflow-providers-postgres >= 6.0 requires apache-airflow >= 2.11.0 (which pulls in 3.x).
```

```bash
# ❌ Wrong — no version pin, no constraints
pip install apache-airflow-providers-postgres

# ✅ Correct — pinned version with constraints
pip install "apache-airflow-providers-postgres==5.14.0" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"
```

---

**Scenario 28:**
> XCom pull returns `None` in PythonOperator but the sensor ran successfully.

**Cause and Fix:**

```
Cause: In a Sensor's poke() method, XCom must be pushed using
context["task_instance"].xcom_push() not ti.xcom_push().
If ti.xcom_push() is used, the push silently fails.
```

```python
# ❌ Wrong — ti is not available in poke()
def poke(self, context):
    data = fetch_data()
    ti.xcom_push(key="result", value=data)   # NameError or silent fail
    return True

# ✅ Correct — use context["task_instance"]
def poke(self, context):
    data = fetch_data()
    context["task_instance"].xcom_push(key="result", value=data)
    return True

# Then in PythonOperator
def my_task(ti):
    data = ti.xcom_pull(task_ids="my_sensor", key="result")
    if not data:
        raise ValueError("XCom data missing!")
```

---

*Scenario-Based Interview Q&A — Apache Airflow 2.10.4*
*Covers: DAG Design, Debugging, Sensors, XCom, Database, Performance, Setup, Real Errors*
