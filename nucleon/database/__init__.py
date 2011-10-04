from psycopg2 import IntegrityError
from .pgpool import PostgresConnectionPool

db = PostgresConnectionPool(
    host='127.0.0.1',
    database='vreg',
    user='vreg',
    password='IeX0ohte',
)
