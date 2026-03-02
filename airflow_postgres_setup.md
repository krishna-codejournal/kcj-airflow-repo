# Airflow — Switch Metadata DB from SQLite to PostgreSQL

> **Environment:** WSL (Windows Subsystem for Linux) | Python 3.12 | Airflow 2.10.4

---

## Table of Contents
1. [Why Switch from SQLite to PostgreSQL?](#why-switch-from-sqlite-to-postgresql)
2. [Step 1 — Install PostgreSQL](#step-1--install-postgresql)
3. [Step 2 — Create Airflow Database and User](#step-2--create-airflow-database-and-user)
4. [Step 3 — Initialize Airflow Config](#step-3--initialize-airflow-config)
5. [Step 4 — Update the Connection String](#step-4--update-the-connection-string)
6. [Step 5 — Re-initialize Airflow with PostgreSQL](#step-5--re-initialize-airflow-with-postgresql)
7. [Step 6 — Create Admin User](#step-6--create-admin-user)
8. [Step 7 — Start Airflow](#step-7--start-airflow)
9. [Verify Setup](#verify-setup)
10. [Connection String Reference](#connection-string-reference)
11. [Common Errors & Fixes](#common-errors--fixes)

---

## Why Switch from SQLite to PostgreSQL?

| Feature | SQLite | PostgreSQL |
|---|---|---|
| Concurrent writes | ❌ Not supported | ✅ Fully supported |
| Production ready | ❌ No | ✅ Yes |
| Scheduler + Webserver simultaneous writes | ❌ Can corrupt DB | ✅ Handled safely |
| Recommended for Airflow | ❌ Dev only | ✅ Yes |

> ⚠️ **Never use SQLite in production.** The Airflow Scheduler and Webserver write to the metadata DB simultaneously — SQLite cannot handle this and may cause data corruption.

---

## Step 1 — Install PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

Verify PostgreSQL is running:

```bash
sudo service postgresql status
```

---

## Step 2 — Create Airflow Database and User

Connect to PostgreSQL as the default `postgres` superuser:

```bash
sudo -u postgres psql
```

Inside the psql shell, run:

```sql
CREATE DATABASE airflow_db;
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
ALTER DATABASE airflow_db OWNER TO airflow_user;
\q
```

> 💡 Replace `airflow_user` and `airflow_pass` with your own secure credentials.

---

## Step 3 — Initialize Airflow Config

If you haven't initialized Airflow yet, run:

```bash
airflow db init
```

This creates the `airflow.cfg` file in your `AIRFLOW_HOME` directory.

### Find your AIRFLOW_HOME

```bash
echo $AIRFLOW_HOME
```

If not set, Airflow defaults to the current working directory or `~/airflow`. Check where `airflow.cfg` was created:

```bash
# Check project directory
ls ~/projects/kcj-airflow-repo/

# Or default home
ls ~/airflow/
```

Confirm the config file location:

```bash
cat ~/projects/kcj-airflow-repo/airflow.cfg | grep sql_alchemy_conn
# Output: sql_alchemy_conn = sqlite:////home/harry/projects/kcj-airflow-repo/airflow.db
```

---

## Step 4 — Update the Connection String

Use `sed` to replace the SQLite connection string with PostgreSQL directly from the terminal:

```bash
sed -i 's|sql_alchemy_conn = sqlite:////home/harry/projects/kcj-airflow-repo/airflow.db|sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db|' ~/projects/kcj-airflow-repo/airflow.cfg
```

> ⚠️ Replace the SQLite path with your actual path if it differs.

Verify the change was applied:

```bash
cat ~/projects/kcj-airflow-repo/airflow.cfg | grep sql_alchemy_conn
```

Expected output:
```
sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db
```

### Alternatively — Edit Manually with nano

```bash
nano ~/projects/kcj-airflow-repo/airflow.cfg
```

Find:
```ini
sql_alchemy_conn = sqlite:////home/harry/projects/kcj-airflow-repo/airflow.db
```

Replace with:
```ini
sql_alchemy_conn = postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## Step 5 — Re-initialize Airflow with PostgreSQL

```bash
airflow db init
```

Expected output:
```
DB: postgresql+psycopg2://airflow_user:***@localhost:5432/airflow_db
Context impl PostgresqlImpl.
Initialization done
```

> ✅ If you see `PostgresqlImpl` in the output, Airflow is now using PostgreSQL.

---

## Step 6 — Create Admin User

Since the database is fresh, recreate your admin user:

```bash
airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin
```

---

## Step 7 — Start Airflow

Open **two separate terminals**:

**Terminal 1 — Webserver:**
```bash
source ~/projects/kcj-airflow-repo/.venv/bin/activate
airflow webserver --port 8080
```

**Terminal 2 — Scheduler:**
```bash
source ~/projects/kcj-airflow-repo/.venv/bin/activate
airflow scheduler
```

Open browser and navigate to:
```
http://localhost:8080
```

---

## Verify Setup

### Check Airflow is using PostgreSQL

```bash
airflow config get-value database sql_alchemy_conn
# Expected: postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db
```

### Check DB connection is healthy

```bash
airflow db check
# Expected: Connection successful
```

### Verify Airflow tables exist in PostgreSQL

```bash
sudo -u postgres psql -d airflow_db -c "\dt"
```

You should see a list of `airflow_*` tables confirming all metadata tables were created successfully.

---

## Connection String Reference

| Component | Example Value |
|---|---|
| Driver | `postgresql+psycopg2` |
| User | `airflow_user` |
| Password | `airflow_pass` |
| Host | `localhost` |
| Port | `5432` |
| Database | `airflow_db` |
| **Full string** | `postgresql+psycopg2://airflow_user:airflow_pass@localhost:5432/airflow_db` |

---

## Common Errors & Fixes

### ❌ `cat: /home/harry/airflow/airflow.cfg: No such file or directory`

**Cause:** `airflow db init` hasn't been run yet, or `AIRFLOW_HOME` is pointing to a different directory.

**Fix:**
```bash
# Run init first
airflow db init

# Then check where the config was created
echo $AIRFLOW_HOME
ls ~/projects/kcj-airflow-repo/
```

---

### ❌ `command not found` when pasting connection string in terminal

**Cause:** The connection string was pasted directly into the terminal instead of inside the config file.

**Fix:** Use `sed` to update the file safely:
```bash
sed -i 's|sql_alchemy_conn = sqlite:///...|sql_alchemy_conn = postgresql+psycopg2://...|' ~/projects/kcj-airflow-repo/airflow.cfg
```

---

### ❌ `could not connect to server: Connection refused`

**Cause:** PostgreSQL service is not running.

**Fix:**
```bash
sudo service postgresql start
sudo service postgresql status
```

---

### ❌ `FATAL: password authentication failed for user "airflow_user"`

**Cause:** Wrong password in the connection string or user not created correctly.

**Fix:** Recreate the user in psql:
```bash
sudo -u postgres psql
```
```sql
DROP USER IF EXISTS airflow_user;
CREATE USER airflow_user WITH PASSWORD 'airflow_pass';
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
\q
```

---

### ❌ `FATAL: database "airflow_db" does not exist`

**Cause:** The database was never created in PostgreSQL.

**Fix:**
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE airflow_db;
GRANT ALL PRIVILEGES ON DATABASE airflow_db TO airflow_user;
\q
```

---

*Guide based on Apache Airflow 2.10.4 | Python 3.12 | WSL Ubuntu*


--- 
Let's verify your connection was saved correctly:

(.venv) harry@Kisna-Warrior2:~/projects/kcj-airflow-repo$ airflow connections get postgres_default

id | conn_id          | conn_type | description | host      | schema   | login        | password     | port | is_encrypted | is_extra_encrypted | extra_dejson | get_uri
===+==================+===========+=============+===========+==========+==============+==============+======+==============+====================+==============+=================================================
42 | postgres_default | postgres  |             | localhost | postgres | airflow_user | airflow_pass | 5432 | False        | False              | {}           | postgres://airflow_user:airflow_pass@localhost:5
   |                  |           |             |           |          |              |              |      |              |                    |              | 432/postgres