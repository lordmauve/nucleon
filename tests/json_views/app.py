from nucleon.framework import Application

app = Application()


@app.view('/')
def version(request):
    return {'version': '0.0.1'}


@app.view('/path-based/(.*)')
def some_path(request, path):
    return {'path': path}
