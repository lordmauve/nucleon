import time
from nucleon.database import IntegrityError
from nucleon.database.api import Database

db = Database('database')

base_select = db.select('SELECT * FROM test')

select_with_params = db.select(
    query='SELECT * FROM test WHERE name=%(name)s AND id=%(id)s'
)

select_with_positional_params = db.select(
    query='SELECT * FROM test WHERE id=%s AND name=%s'
)


select_names = db.select('SELECT name from test ORDER BY id ASC')

simple_insert = db.make_query("""
INSERT INTO test(name) VALUES(%(name)s) RETURNING id;
""")


@db.transaction()
def do_insert(q, name):
    """Transaction to insert a value into the test table."""
    qry = 'INSERT INTO test(name) VALUES(%s) RETURNING id'
    return q.query(qry, (name,)).value


@db.transaction()
def insert_with_id(q, id, name):
    """Transaction to insert a value into the test table."""
    q('INSERT INTO test(id, name) VALUES(%(id)s, %(name)s)',
        id=id, name=name
    )


@db.transaction()
def slow_insert(q, sem):
    """transaction that gives us the opportunity to block."""
    q('insert into test(id, name) values(%s, %s)', 5, 'five')
    sem.acquire()
    try:
        return q(
            'insert into test(id, name) values(%s, %s)',
            7, 'seven'
        )
    except IntegrityError:
        pass  # we expect this, so silence the exception


@db.transaction(retries=3)
def retryable_transaction(q):
    """A transaction that will probably succeed if retried enough times."""
    lastid = q('SELECT max(id) FROM test').value
    time.sleep(1)
    return q(
        'insert into test(id, name) values(%s, %s)',
        lastid + 1, 'a%s' % lastid
    )
