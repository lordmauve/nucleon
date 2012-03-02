from nucleon.database.api import Database

db = Database('database')

base_select = db.select('SELECT * FROM test')

select_with_params = db.select(
    query='SELECT * FROM test WHERE name=%(name)s AND id=%(id)s'
)

select_with_positional_params = db.select(
    query='SELECT * FROM test WHERE id=%s AND name=%s'
)


select_names = db.select('SELECT name from test')
