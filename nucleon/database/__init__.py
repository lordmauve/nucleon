from psycopg2 import IntegrityError, OperationalError
from .pgpool import PostgresConnectionPool


class ConnectionFailed(OperationalError):
    """The connection to the server was not established."""
