import datetime
from nucleon.framework import Application

app = Application()


@app.view('/')
def version(request):
    return {'version': '0.0.1'}


@app.view('/path-based/(.*)')
def some_path(request, path):
    return {'path': path}


@app.view('/dates-naive')
def dates_naive(request):
    some_instant = datetime.datetime(
        year=2012,
        month=2,
        day=21,
        hour=11,
        minute=57,
        second=11,
        microsecond=451137
    )
    return {
        'date': some_instant.date(),
        'datetime': some_instant,
        'time': some_instant.time()
    }


class ConstantOffsetTimezone(datetime.tzinfo):
    """Simple timezone that maintains a constant offset from UTC."""
    def __init__(self, offset=0):
        self.offset = offset * 3600

    def utcoffset(self, dt):
        return datetime.timedelta(seconds=self.offset)

    def dst(self, dt):
        return datetime.timedelta(seconds=self.offset)

UTC = ConstantOffsetTimezone(0)
BST = ConstantOffsetTimezone(1)


@app.view('/dates-utc')
def dates_utc(request):
    """Return some information about a particular time in UTC."""
    some_instant = datetime.datetime(
        year=2012,
        month=2,
        day=21,
        hour=11,
        minute=57,
        second=11,
        microsecond=451137,
        tzinfo=UTC
    )
    return {
        'date': some_instant.date(),
        'datetime': some_instant,
        'time': some_instant.timetz()
    }


@app.view('/dates-bst')
def dates_bst(request):
    """Return some information about a particular time in BST."""
    some_instant = datetime.datetime(
        year=2012,
        month=2,
        day=21,
        hour=11,
        minute=57,
        second=11,
        microsecond=451137,
        tzinfo=BST
    )
    return {
        'date': some_instant.date(),
        'datetime': some_instant,
        'time': some_instant.timetz()
    }
