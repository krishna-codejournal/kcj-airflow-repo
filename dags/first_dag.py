from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'harry',
    'retries': 5,
    'retry_delay': timedelta(minutes=2)
}

with DAG(
    dag_id='first_dag',
    description='This is our first dag that we write',
    start_date=datetime(2021, 7, 29, 2),
    schedule='@daily',          
    default_args=default_args,
    catchup=False               # Recommended Otherwise Airflow will try to run all historical dates since 2021
) as dag:

    task1 = BashOperator(
        task_id='first_task',
        bash_command="echo hello world"
    )

    task2 = BashOperator(
        task_id='second_task',
        bash_command="echo Hey, I am Task2"
    )

    task1.set_downstream(task2)