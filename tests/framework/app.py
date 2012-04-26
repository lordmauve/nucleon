from nucleon.http import Http404, JsonErrorResponse
from nucleon.framework import Application
app = Application()


# Views to expose request routing and handling

@app.view('/$')
def fail(request):
    raise IOError("Let's imagine something failed here.")


def handle_post(request):
    return dict(request.POST)


app.add_view('/post$', {'POST': handle_post, 'PUT': handle_post})


# Views to serve various response types


@app.view('/404')
def missing(request):
    raise Http404("This thing didn't exist")


@app.view('/400')
def client_error(request):
    return JsonErrorResponse({
        'error': 'SOME_ERROR',
        'message': 'Some message'
    })
