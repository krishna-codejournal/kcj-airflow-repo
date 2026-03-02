from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from datetime import datetime
import requests
import logging


# Get logger
log = logging.getLogger(__name__)

class ISAPIAvailableSensor(BaseSensorOperator):
    @apply_defaults
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def poke(self, context):
        url ="https://raw.githubusercontent.com/marclamberti/datasets/refs/heads/main/fakeuser.json"
        log.info("Poking API: %s", url)

        try:
            response = requests.get(url)
            log.info("API response status code: %s", response.status_code)

            if response.status_code == 200:
                fake_user = response.json()
                log.info("API is available. User fetched: %s", fake_user.get("id"))
                context["task_instance"].xcom_push(key="fake_user", value=fake_user)
                return True
            else:
                log.warning("API returned non-200 status: %s", response.status_code)
                return False

        except requests.exceptions.ConnectionError:
            log.error("Connection error — API is unreachable")
            return False
        except requests.exceptions.Timeout:
            log.error("Request timed out")
            return False
        except Exception as e:
            log.error("Unexpected error: %s", str(e))
            return False

def _extract_user(ti):
    log.info("Starting extract_user task")
    fake_user = ti.xcom_pull(task_ids="is_api_available", key="fake_user")
    if not fake_user:
        log.error("No user data found in XCom from is_api_available")
        raise ValueError("XCom data is missing — is_api_available may have failed")

    log.info("Raw user data pulled from XCom: %s", fake_user)

    user = {
        "id": fake_user["id"],
        "firstname": fake_user["personalInfo"]["firstName"],
        "lastname": fake_user["personalInfo"]["lastName"],
        "email": fake_user["personalInfo"]["email"],
    }

    log.info("Extracted user: id=%s, email=%s", user["id"], user["email"])
    return user

with DAG(
    dag_id="user_processing",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False
) as dag:

    create_table = SQLExecuteQueryOperator(
        task_id="create_user_table",
        conn_id="postgres_default",
        sql="""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    is_api_available = ISAPIAvailableSensor(
        task_id="is_api_available",
        mode ="poke",
        poke_interval=60,
        timeout=300
    )

    extract_user = PythonOperator(
        task_id="extract_user",
        python_callable=_extract_user
    )

    create_table >> is_api_available >> extract_user