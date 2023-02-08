from procrastinate import App
from procrastinate.contrib.sqlalchemy import SQLAlchemyPsycopg2Connector
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://")
app = App(connector=SQLAlchemyPsycopg2Connector()).open(engine)