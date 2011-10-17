"""Test app that queries the database for arithmetic operations."""

from nucleon.framework import Application
app = Application()


@app.view('/(\d+)')
def dbsquared(request, x):
    x = long(x)
    db = app.get_database()
    with db.cursor() as c:
        c.execute('SELECT %s ^ 2;', (x,))
        res = c.fetchone()[0]
    return {'x': x, 'x^2': res}
