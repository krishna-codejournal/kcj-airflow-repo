# Airflow Sensors — Complete Guide with Examples

> **Environment:** Apache Airflow 2.10.4

---

## Table of Contents
1. [What is a Sensor?](#what-is-a-sensor)
2. [How Sensors Work](#how-sensors-work)
3. [poke() Method — Deep Dive](#poke-method--deep-dive)
4. [context — Deep Dive](#context--deep-dive)
5. [Sensor Modes](#sensor-modes)
6. [Built-in Sensors](#built-in-sensors)
7. [Custom Sensor](#custom-sensor)
8. [Real World Example — User Processing DAG](#real-world-example--user-processing-dag)
9. [Sensor with XCom](#sensor-with-xcom)
10. [Sensor Timeout & Retries](#sensor-timeout--retries)
11. [Sensors vs Operators](#sensors-vs-operators)
12. [Best Practices](#best-practices)
13. [Common Errors & Fixes](#common-errors--fixes)

---

## What is a Sensor?

A **Sensor** is a special type of Airflow Operator that **waits for a condition to be met** before allowing the downstream tasks to proceed.

Think of it like a **gatekeeper** — it keeps checking a condition repeatedly (polling) and only opens the gate when the condition is `True`.

```
┌─────────────────────────────────────────────────┐
│                   Sensor Task                   │
│                                                 │
│   poke() → False → wait → poke() → False →     │
│   wait → poke() → True ✅ → downstream runs    │
└─────────────────────────────────────────────────┘
```

### Common Use Cases

- Wait for a **file to appear** in S3, SFTP, or local filesystem
- Wait for an **API to become available**
- Wait for a **database record** to exist
- Wait for an **external DAG** to complete
- Wait for a **time condition** to be met
- Wait for a **Kafka message** to arrive

---

## How Sensors Work

Every sensor has a `poke()` method that Airflow calls repeatedly at a defined interval.

```
Sensor starts
     │
     ▼
 poke() called
     │
     ├── returns False → wait poke_interval seconds → poke() again
     │
     └── returns True  → sensor succeeds → downstream tasks run
```

### The `poke()` Method

```python
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

class MySensor(BaseSensorOperator):

    @apply_defaults
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def poke(self, context) -> bool:
        # Write your condition check here
        # Return True  → condition met, sensor succeeds
        # Return False → condition not met, sensor waits and retries
        
        condition_met = check_something()
        return condition_met
```

### Key Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `poke_interval` | int | 60 | Seconds to wait between pokes |
| `timeout` | int | 604800 (7 days) | Max seconds to wait before failing |
| `mode` | str | `"poke"` | Execution mode: `poke` or `reschedule` |
| `soft_fail` | bool | `False` | If `True`, marks task as skipped instead of failed on timeout |
| `exponential_backoff` | bool | `False` | Increases wait time between pokes exponentially |

---

## poke() Method — Deep Dive

`poke()` is the **core method** of every sensor. It is the method Airflow calls **repeatedly on a schedule** until it returns `True`.

```python
def poke(self, context) -> bool:
    # your condition check here
    return True or False
```

### Rules of poke()

```
Returns True      → condition met → sensor succeeds → downstream tasks run
Returns False     → condition not met → wait poke_interval → call poke() again
Raises Exception  → sensor fails immediately
```

### You MUST Override It

`poke()` is an **abstract method** in `BaseSensorOperator` — every custom sensor must define it:

```python
from airflow.sensors.base import BaseSensorOperator

class MySensor(BaseSensorOperator):

    # ✅ You must define this — it's abstract in BaseSensorOperator
    def poke(self, context) -> bool:
        result = check_my_condition()
        return result   # True or False
```

If you don't override `poke()`, Airflow will raise:
```
TypeError: Can't instantiate abstract class MySensor with abstract method poke
```

### poke() vs execute() — Sensor vs Operator

| | Sensor `poke()` | Operator `execute()` |
|---|---|---|
| Called | Repeatedly until True | Once |
| Returns | `True` or `False` | Any value |
| Purpose | Check a condition | Perform an action |
| Base class | `BaseSensorOperator` | `BaseOperator` |

---

## context — Deep Dive

`context` is a **Python dictionary** that Airflow automatically passes into `poke()`. It contains **everything about the current task run** — the DAG, task instance, execution date, and much more.

```python
def poke(self, context) -> bool:
    print(type(context))   # <class 'dict'>
    print(context.keys())  # all available keys
```

### What's Inside context?

```python
{
    "dag":              <DAG: user_processing>,
    "task":             <Task: is_api_available>,
    "task_instance":    <TaskInstance: ...>,    # 👈 most used
    "run_id":           "scheduled__2024-01-01T00:00:00+00:00",
    "execution_date":   datetime(2024, 1, 1),
    "ds":               "2024-01-01",           # execution date as string
    "ds_nodash":        "20240101",
    "ts":               "2024-01-01T00:00:00+00:00",
    "prev_ds":          "2023-12-31",
    "next_ds":          "2024-01-02",
    "dag_run":          <DagRun: ...>,
    "conf":             {},                     # DAG run config
    "params":           {},                     # DAG params
    "macros":           <module 'airflow.macros'>,
    "var":              {"value": ..., "json": ...},
    "conn":             <connection proxy>,
}
```

### The Most Important Key — `task_instance`

`context["task_instance"]` gives you the **TaskInstance object** (`ti`) — the same object you get when you write `ti` in a PythonOperator.

```python
def poke(self, context) -> bool:

    # Access task instance via context
    ti = context["task_instance"]

    # Now you can use all TaskInstance methods
    ti.xcom_push(key="result", value={"id": 1})
    ti.xcom_pull(task_ids="another_task", key="some_key")

    log.info("DAG ID: %s", ti.dag_id)
    log.info("Task ID: %s", ti.task_id)
    log.info("Execution date: %s", ti.execution_date)

    return True
```

### Accessing Other context Values

```python
def poke(self, context) -> bool:

    ti             = context["task_instance"]   # TaskInstance object
    execution_date = context["ds"]              # "2024-01-01"
    dag_id         = context["dag"].dag_id      # "user_processing"
    run_id         = context["run_id"]          # "scheduled__2024-01-01..."
    prev_date      = context["prev_ds"]         # "2023-12-31"

    log.info("DAG: %s | Date: %s", dag_id, execution_date)
    return True
```

### Why Does poke() Receive `context` but PythonOperator Gets `ti` Directly?

This is a common point of confusion. Here's why:

```python
# PythonOperator — Airflow inspects parameter names
# and injects matching context variables automatically
def my_python_task(ti, ds, execution_date):
    #               ↑   ↑   ↑
    # Airflow sees these names and injects the right values
    pass


# Sensor poke() — receives the ENTIRE context dict
# because it's a class method, not a standalone function
def poke(self, context):
    ti = context["task_instance"]  # you extract what you need manually
    ds = context["ds"]
```

| | PythonOperator callable | Sensor `poke()` |
|---|---|---|
| How context is passed | Auto-injected by parameter name | Full dict passed as `context` |
| Access `ti` | `def fn(ti):` | `context["task_instance"]` |
| Access date | `def fn(ds):` | `context["ds"]` |
| Access dag | `def fn(dag):` | `context["dag"]` |

### Full Example — Using context in poke()

```python
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
import requests
import logging

log = logging.getLogger(__name__)


class IsApiAvailableSensor(BaseSensorOperator):

    @apply_defaults
    def __init__(self, url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url

    def poke(self, context) -> bool:

        # ── Extract useful things from context ──────────────
        ti             = context["task_instance"]
        execution_date = context["ds"]
        dag_id         = context["dag"].dag_id
        # ────────────────────────────────────────────────────

        log.info("DAG: %s | Date: %s | Checking: %s", dag_id, execution_date, self.url)

        try:
            response = requests.get(self.url, timeout=10)
            log.info("Status code: %s", response.status_code)

            if response.status_code == 200:
                data = response.json()

                # Push result to XCom via context["task_instance"]
                ti.xcom_push(key="fake_user", value=data)

                log.info("API available! Data pushed to XCom.")
                return True    # ✅ condition met

            log.warning("Not ready. Will retry.")
            return False       # ❌ retry

        except Exception as e:
            log.error("Error during poke: %s", str(e))
            return False       # ❌ retry — don't raise, let sensor retry

```

### poke() & context — Summary

| Concept | What it is |
|---|---|
| `poke()` | The method Airflow calls repeatedly to check a condition |
| Returns `True` | Condition met — sensor succeeds |
| Returns `False` | Condition not met — wait and retry |
| `context` | A dictionary Airflow passes with all info about the current run |
| `context["task_instance"]` | The TaskInstance object — use it to push/pull XCom |
| `context["ds"]` | Execution date as string e.g. `"2024-01-01"` |
| `context["dag"]` | The DAG object |
| `context["run_id"]` | The current DAG run ID |

---

## Sensor Modes

Sensors have two execution modes that control how they use Airflow worker slots.

### Mode 1 — `poke` (Default)

The sensor **occupies a worker slot** the entire time it is waiting.

```python
my_sensor = MySensor(
    task_id="my_sensor",
    mode="poke",           # 👈 holds worker slot while waiting
    poke_interval=60,      # check every 60 seconds
    timeout=3600           # give up after 1 hour
)
```

```
Worker Slot occupied:
├── poke() → False → sleep 60s
├── poke() → False → sleep 60s
├── poke() → False → sleep 60s
└── poke() → True  → release slot ✅
```

**When to use:** Short wait times (seconds to a few minutes).

---

### Mode 2 — `reschedule`

The sensor **releases the worker slot** between pokes and reschedules itself.

```python
my_sensor = MySensor(
    task_id="my_sensor",
    mode="reschedule",     # 👈 releases worker slot between pokes
    poke_interval=300,     # check every 5 minutes
    timeout=86400          # give up after 24 hours
)
```

```
Worker Slot:
├── poke() → False → RELEASE slot → reschedule in 300s
│                        ↓
│              [slot free for other tasks]
│                        ↓
├── poke() → False → RELEASE slot → reschedule in 300s
│                        ↓
│              [slot free for other tasks]
│                        ↓
└── poke() → True  → success ✅
```

**When to use:** Long wait times (minutes to hours/days). Much more efficient.

---

### Mode Comparison

| Feature | `poke` | `reschedule` |
|---|---|---|
| Worker slot usage | Held entire time | Released between pokes |
| Best for | Short waits (< 5 min) | Long waits (> 5 min) |
| Resource efficiency | ❌ Less efficient | ✅ More efficient |
| Complexity | Simple | Slightly more complex |

---

## Built-in Sensors

Airflow provides many ready-to-use sensors out of the box.

### 1. FileSensor — Wait for a File

```python
from airflow.sensors.filesystem import FileSensor

wait_for_file = FileSensor(
    task_id="wait_for_file",
    filepath="/mnt/data/input.csv",   # path to check
    poke_interval=30,                  # check every 30 seconds
    timeout=3600,                      # fail after 1 hour
    mode="reschedule"
)
```

---

### 2. HttpSensor — Wait for an API/URL

```python
from airflow.providers.http.sensors.http import HttpSensor

wait_for_api = HttpSensor(
    task_id="wait_for_api",
    http_conn_id="my_api_conn",       # connection ID in Airflow
    endpoint="api/v1/status",         # endpoint to check
    response_check=lambda response: response.json()["status"] == "ready",
    poke_interval=60,
    timeout=3600,
    mode="reschedule"
)
```

---

### 3. SqlSensor — Wait for a DB Record

```python
from airflow.providers.common.sql.sensors.sql import SqlSensor

wait_for_record = SqlSensor(
    task_id="wait_for_record",
    conn_id="postgres",
    sql="SELECT COUNT(*) FROM orders WHERE status = 'ready'",
    # Sensor succeeds when query returns a non-zero/non-null result
    poke_interval=60,
    timeout=7200,
    mode="reschedule"
)
```

---

### 4. S3KeySensor — Wait for S3 File

```python
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

wait_for_s3 = S3KeySensor(
    task_id="wait_for_s3_file",
    bucket_name="my-bucket",
    bucket_key="data/input/{{ ds }}/file.csv",
    aws_conn_id="aws_default",
    poke_interval=60,
    timeout=3600,
    mode="reschedule"
)
```

---

### 5. ExternalTaskSensor — Wait for Another DAG's Task

```python
from airflow.sensors.external_task import ExternalTaskSensor

wait_for_upstream = ExternalTaskSensor(
    task_id="wait_for_upstream_dag",
    external_dag_id="upstream_dag",
    external_task_id="final_task",
    poke_interval=60,
    timeout=3600,
    mode="reschedule"
)
```

---

### 6. TimeDeltaSensor — Wait for a Time Duration

```python
from airflow.sensors.time_delta import TimeDeltaSensor
from datetime import timedelta

wait_for_time = TimeDeltaSensor(
    task_id="wait_30_minutes",
    delta=timedelta(minutes=30)
)
```

---

## Custom Sensor

When built-in sensors don't cover your use case, build your own by extending `BaseSensorOperator`.

### Basic Custom Sensor Template

```python
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
import logging

log = logging.getLogger(__name__)

class MyCustomSensor(BaseSensorOperator):

    @apply_defaults
    def __init__(
        self,
        my_param: str,       # custom parameters
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.my_param = my_param   # store custom params

    def poke(self, context) -> bool:
        log.info("Checking condition with param: %s", self.my_param)

        # Your condition logic here
        result = check_some_condition(self.my_param)

        if result:
            log.info("Condition met! Sensor succeeding.")
            return True

        log.info("Condition not met. Will retry.")
        return False
```

### Using the Custom Sensor

```python
my_sensor = MyCustomSensor(
    task_id="my_custom_sensor",
    my_param="some_value",
    poke_interval=60,
    timeout=3600,
    mode="reschedule"
)
```

---

## Real World Example — User Processing DAG

A complete DAG with a custom sensor that checks if an API is available before proceeding.

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


# ── Custom Sensor ─────────────────────────────────────────────────────────────
class IsApiAvailableSensor(BaseSensorOperator):
    """
    Sensor that checks if the fake user API is available.
    Pushes the API response to XCom when successful.
    """

    @apply_defaults
    def __init__(self, url: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url

    def poke(self, context) -> bool:
        log.info("Poking API at: %s", self.url)

        try:
            response = requests.get(self.url, timeout=10)
            log.info("API status code: %s", response.status_code)

            if response.status_code == 200:
                data = response.json()
                log.info("API is available. Pushing data to XCom.")

                # Push response to XCom for downstream tasks
                context["task_instance"].xcom_push(
                    key="fake_user",
                    value=data
                )
                return True  # ✅ condition met

            log.warning("API returned: %s. Retrying...", response.status_code)
            return False  # ❌ condition not met, retry

        except requests.exceptions.Timeout:
            log.error("Request timed out. Retrying...")
            return False

        except requests.exceptions.ConnectionError:
            log.error("Connection error. Retrying...")
            return False

        except Exception as e:
            log.error("Unexpected error: %s", str(e))
            return False


# ── Task Functions ────────────────────────────────────────────────────────────
def _extract_user(ti):
    log.info("Pulling user data from XCom")

    fake_user = ti.xcom_pull(
        task_ids="is_api_available",
        key="fake_user"
    )

    if not fake_user:
        log.error("No data in XCom from sensor")
        raise ValueError("XCom data missing from is_api_available")

    user = {
        "id": fake_user["id"],
        "firstname": fake_user["personalInfo"]["firstName"],
        "lastname": fake_user["personalInfo"]["lastName"],
        "email": fake_user["personalInfo"]["email"],
    }

    log.info("Extracted user: id=%s email=%s", user["id"], user["email"])
    return user


def _process_user(ti):
    user = ti.xcom_pull(task_ids="extract_user")
    log.info("Processing user: %s %s", user["firstname"], user["lastname"])
    # Further processing logic here...


# ── DAG Definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id="user_processing",
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
            lastname VARCHAR(255),
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    is_api_available = IsApiAvailableSensor(
        task_id="is_api_available",
        url="https://raw.githubusercontent.com/marclamberti/datasets/refs/heads/main/fakeuser.json",
        poke_interval=30,
        timeout=300,
        mode="reschedule"    # 👈 efficient — releases slot between pokes
    )

    extract_user = PythonOperator(
        task_id="extract_user",
        python_callable=_extract_user
    )

    process_user = PythonOperator(
        task_id="process_user",
        python_callable=_process_user
    )

    # Task pipeline
    create_table >> is_api_available >> extract_user >> process_user
```

### DAG Flow

```
create_table
     │
     ▼
is_api_available  ←── pokes every 30s until API returns 200
     │                 pushes response to XCom on success
     ▼
extract_user      ←── pulls raw data from XCom, extracts fields
     │                 returns clean user dict (auto-pushed to XCom)
     ▼
process_user      ←── pulls clean user dict from XCom
```

---

## Sensor with XCom

Sensors can push data to XCom inside `poke()` so downstream tasks can use it.

```python
class DataSensor(BaseSensorOperator):

    def poke(self, context) -> bool:
        data = fetch_data()

        if data:
            # Push to XCom via context
            context["task_instance"].xcom_push(
                key="fetched_data",
                value=data
            )
            return True
        return False


def use_data(ti):
    # Pull in downstream task
    data = ti.xcom_pull(
        task_ids="data_sensor",
        key="fetched_data"
    )
    print(f"Got data: {data}")
```

---

## Sensor Timeout & Retries

### Timeout — Give Up After N Seconds

```python
my_sensor = MySensor(
    task_id="my_sensor",
    poke_interval=60,
    timeout=3600,       # fail after 1 hour
    soft_fail=False     # True = skip task instead of fail
)
```

### soft_fail — Skip Instead of Fail

```python
my_sensor = MySensor(
    task_id="my_sensor",
    timeout=300,
    soft_fail=True      # marks task as SKIPPED instead of FAILED on timeout
)
```

### Exponential Backoff — Increase Wait Time Over Time

```python
my_sensor = MySensor(
    task_id="my_sensor",
    poke_interval=30,
    exponential_backoff=True,   # 30s → 60s → 120s → 240s...
    timeout=3600
)
```

### Timeout Values Reference

```python
# Common timeout values
30          # 30 seconds
300         # 5 minutes
3600        # 1 hour
86400       # 1 day
604800      # 7 days (default)
```

---

## Sensors vs Operators

| Feature | Sensor | Operator |
|---|---|---|
| Purpose | Wait for a condition | Execute an action |
| Core method | `poke()` | `execute()` |
| Returns | `True` / `False` | Any value |
| Polling | ✅ Yes — retries until True | ❌ No — runs once |
| Worker slot | Held (poke) or released (reschedule) | Held during execution |
| Examples | FileSensor, HttpSensor, SqlSensor | PythonOperator, BashOperator |
| Base class | `BaseSensorOperator` | `BaseOperator` |

---

## Best Practices

### 1. Always Use `reschedule` Mode for Long Waits

```python
# ✅ Good — releases worker slot between pokes
my_sensor = MySensor(
    task_id="my_sensor",
    mode="reschedule",
    poke_interval=300   # 5 minutes
)

# ❌ Bad for long waits — holds worker slot
my_sensor = MySensor(
    task_id="my_sensor",
    mode="poke",        # holding slot for hours wastes resources
    poke_interval=3600
)
```

### 2. Always Set a Timeout

```python
# ✅ Good — won't run forever
my_sensor = MySensor(
    task_id="my_sensor",
    timeout=3600        # fail after 1 hour
)

# ❌ Bad — could run for 7 days (default)
my_sensor = MySensor(
    task_id="my_sensor"
    # no timeout set
)
```

### 3. Add Proper Logging in poke()

```python
def poke(self, context) -> bool:
    log.info("Checking condition...")   # log every poke attempt
    result = check_condition()
    if result:
        log.info("Condition met!")
    else:
        log.info("Not ready yet. Retrying in %s seconds", self.poke_interval)
    return result
```

### 4. Handle Exceptions Gracefully

```python
def poke(self, context) -> bool:
    try:
        result = check_condition()
        return result
    except ConnectionError:
        log.warning("Connection failed, will retry")
        return False      # return False to retry, not raise
    except Exception as e:
        log.error("Unexpected error: %s", str(e))
        raise             # raise to fail the task immediately
```

### 5. Use `soft_fail` for Optional Conditions

```python
# If API not available, just skip instead of failing entire DAG
my_sensor = MySensor(
    task_id="optional_check",
    timeout=300,
    soft_fail=True   # skips task gracefully on timeout
)
```

---

## Common Errors & Fixes

### ❌ `AirflowSensorTimeout` — Sensor timed out

**Cause:** Condition never became `True` within the timeout period.

**Fix:**
```python
# Increase timeout or investigate why condition never met
my_sensor = MySensor(
    task_id="my_sensor",
    timeout=7200,       # increase timeout
    soft_fail=True      # or use soft_fail to skip gracefully
)
```

---

### ❌ Worker slots exhausted — Too many poke-mode sensors

**Cause:** Multiple sensors in `poke` mode all holding worker slots simultaneously.

**Fix:**
```python
# Switch all long-running sensors to reschedule mode
my_sensor = MySensor(
    task_id="my_sensor",
    mode="reschedule"   # 👈 releases slot between pokes
)
```

---

### ❌ `poke()` pushing XCom but downstream task gets `None`

**Cause:** Using `ti.xcom_push()` in sensor instead of `context["task_instance"].xcom_push()`.

**Fix:**
```python
# ❌ Wrong — ti is not available in poke()
def poke(self, context):
    ti.xcom_push(key="data", value=result)

# ✅ Correct — use context["task_instance"]
def poke(self, context):
    context["task_instance"].xcom_push(key="data", value=result)
```

---

### ❌ Sensor retrying even after condition is met

**Cause:** `poke()` is not returning `True` explicitly.

**Fix:**
```python
# ❌ Wrong — no explicit return
def poke(self, context):
    if condition_met():
        do_something()
    # Missing return True!

# ✅ Correct — always return True or False
def poke(self, context):
    if condition_met():
        return True
    return False
```

---

## Quick Reference

```python
# Import
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

# Custom sensor template
class MySensor(BaseSensorOperator):
    @apply_defaults
    def __init__(self, my_param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.my_param = my_param

    def poke(self, context) -> bool:
        # Push to XCom
        context["task_instance"].xcom_push(key="result", value=data)
        return True or False   # True = done, False = retry

# Usage
sensor = MySensor(
    task_id="my_sensor",
    my_param="value",
    poke_interval=30,      # check every 30 seconds
    timeout=3600,          # fail after 1 hour
    mode="reschedule",     # efficient mode
    soft_fail=False        # True = skip on timeout
)
```

---

*Guide based on Apache Airflow 2.10.4 | Python 3.12*
