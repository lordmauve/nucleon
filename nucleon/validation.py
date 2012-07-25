from .http import JsonErrorResponse


def validation_errors(e):
    """Helper method that turns a formencode.Invalid error
    into a JSON response."""
    out = {}
    if e.error_dict:
        for k, v in e.error_dict.items():
            out[k] = unicode(v)
        return JsonErrorResponse({
            'error': 'INVALID_PARAMETERS',
            'messages': out
        })
    else:
        return JsonErrorResponse({
            'error': 'INVALID_PARAMETER',
            'message': unicode(e)
        })
