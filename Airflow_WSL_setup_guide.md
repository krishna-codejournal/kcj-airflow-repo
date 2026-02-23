# Dual Virtual Environment Workflow for Apache Airflow (Windows + WSL)

This guide explains how to:

✅ Develop DAGs locally on Windows with full editor support\
✅ Run Airflow reliably inside WSL (Linux)\
✅ Avoid permission, path, and compatibility issues

------------------------------------------------------------------------

## 🧠 Architecture Overview

  --------------------------------------------------------------------------------------------
  Layer              Purpose                  Location
  ------------------ ------------------------ ------------------------------------------------
  Windows venv       Code editing, imports,   `.venv_win`
                     autocomplete             

  WSL venv           Real Airflow execution   `~/projects/kcj-airflow-repo/.venv`

  DAGs               Shared project code      `D:\krishna-codejournal\kcj-airflow-repo\dags`
  --------------------------------------------------------------------------------------------

------------------------------------------------------------------------

# ✅ Step 1: Create Development venv on Windows

``` powershell
cd D:\krishna-codejournal\kcj-airflow-repo
python -m venv .venv_win
.venv_win\Scripts\activate
python -m pip install --upgrade pip
```

------------------------------------------------------------------------

# 📦 Step 2: Install Airflow Package for Imports

``` powershell
pip install apache-airflow==2.9.3
```

This is only for:

✔ Python imports\
✔ IDE autocomplete\
✔ Linting & type checking

(No scheduler/webserver on Windows)

------------------------------------------------------------------------

# 🧠 Step 3: Configure Your Code Editor

In VS Code:

    Ctrl + Shift + P → Python: Select Interpreter → .venv_win

------------------------------------------------------------------------

# 🚀 Step 4: Runtime Happens in WSL

WSL Airflow reads DAGs directly from:

``` text
/mnt/d/krishna-codejournal/kcj-airflow-repo/dags
```

------------------------------------------------------------------------

# 📁 Recommended Project Layout

``` text
kcj-airflow-repo/
├── dags/
│   ├── etl/
│   ├── monitoring/
│   └── demos/
├── shared/
│   ├── db_utils.py
│   └── validators.py
├── .venv_win/
└── README.md
```

------------------------------------------------------------------------

# 🎯 Why This Workflow Works

✔ Windows productivity tools\
✔ Linux runtime stability\
✔ No syncing needed\
✔ No permission problems

------------------------------------------------------------------------

Happy DAG building 🚀




# Apache Airflow WSL Setup Guide (Permanent Configuration)

This guide walks through installing Apache Airflow in WSL (Ubuntu) and
permanently configuring paths for a clean Windows + Linux workflow.

------------------------------------------------------------------------

## 🎯 Target Architecture

  Purpose        Path
  -------------- --------------------------------------------------
  AIRFLOW_HOME   \~/projects/kcj-airflow-repo
  DAGs Folder    /mnt/d/krishna-codejournal/kcj-airflow-repo/dags

------------------------------------------------------------------------

# ✅ Step 0: Prerequisites

``` bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential
```

------------------------------------------------------------------------

# ✅ Step 1: Create Project Runtime

``` bash
mkdir -p ~/projects/kcj-airflow-repo
cd ~/projects/kcj-airflow-repo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

------------------------------------------------------------------------

# ✅ Step 2: Install Apache Airflow

``` bash
AIRFLOW_VERSION=2.9.3
PYTHON_VERSION=3.12
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install "apache-airflow==$AIRFLOW_VERSION" --constraint $CONSTRAINT_URL
airflow version
```

------------------------------------------------------------------------

# ✅ Step 3: Permanent Environment Variables

``` bash
nano ~/.bashrc
```

Add:

``` bash
export AIRFLOW_HOME=$HOME/projects/kcj-airflow-repo
export AIRFLOW__CORE__DAGS_FOLDER=/mnt/d/krishna-codejournal/kcj-airflow-repo/dags
```

Reload:

``` bash
source ~/.bashrc
```

------------------------------------------------------------------------

# ✅ Step 4: Initialize Airflow

``` bash
airflow db reset -y
airflow db init
```

Create admin:

``` bash
airflow users create \
 --username admin \
 --firstname Krishna \
 --lastname T \
 --role Admin \
 --email admin@example.com \
 --password admin
```

------------------------------------------------------------------------

# ✅ Step 5: Start Services

Terminal 1:

``` bash
airflow webserver -p 8080
```

Terminal 2:

``` bash
airflow scheduler
```

UI: http://localhost:8080

------------------------------------------------------------------------

# 🧠 Health Check

``` bash
airflow config get-value core dags_folder
airflow info | grep AIRFLOW_HOME
```

------------------------------------------------------------------------

# 🧩 Why This Setup Works

✔ Windows development\
✔ Linux runtime stability\
✔ No permission issues\
✔ Production-like workflow

------------------------------------------------------------------------

Happy building 🚀
