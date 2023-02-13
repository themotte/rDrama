from procrastinate import App, AiopgConnector
from files.helpers.const import DATABASE_URL

# from procrastinate.contrib.sqlalchemy import SQLAlchemyPsycopg2Connector
# from sqlalchemy import create_engine

## Sqlalchemy (synchronous) engine creation:
# engine = create_engine(DATABASE_URL)
# syncApp = App(connector=SQLAlchemyPsycopg2Connector()).open(engine)

## Main (async) procrastinate connector:
app = App(connector=AiopgConnector(dsn=DATABASE_URL))

# TODO: Get schema into the postgres db via a migration rather than calling `procrastinate --app=procrastinator.py schema --apply`
# see https://procrastinate.readthedocs.io/en/stable/quickstart.html#prepare-the-database for details

# TODO: Figure out command line syntax to create new tasks
# TODO: Figure out command line syntax to schedule tasks
# TODO: Build tasks for recurring posts, etc.

@app.task(name="task_sum")
def task_sum(a, b):
    return a + b

if __name__ == "__main__":
    # Defer/queue 'task_sum' to a non-specific point in the future:
    task_sum.defer(a=1, b=3)