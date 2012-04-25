from nucleon.framework import Application
app = Application()


@app.view('/$')
def fail(request):
    raise IOError("Let's imagine something failed here.")


def handle_post(request):
    return dict(request.POST)


app.add_view('/post$', {'POST': handle_post, 'PUT': handle_post})
