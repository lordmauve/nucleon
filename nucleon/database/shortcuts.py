from collections import OrderedDict

from . import db
from ..framework import Http404


__all__ = ['db_select_first', 'db_select_list']


DEFAULT_ERROR_NOT_FOUND = 'No such object was found in the database.'


def db_select_first(query, params=(), error_not_found=DEFAULT_ERROR_NOT_FOUND):
    """Query the database and return the first row as a dictionary.
    
    If no row is returned for the given query, raises Http404, with the message
    error_not_found.
    """

    with db.cursor() as c:
        c.execute(query, params)
        r = c.fetchone()
        if r is None:
            raise Http404(error_not_found)

        # Use OrderedDict as the JSON is more legible if the key order matches
        # the order of columns in the database.
        return OrderedDict(zip([col[0] for col in c.description], r))


def db_select_list(query, params=()):
    """Query the database, returning the results as a list of dictionaries."""

    with db.cursor() as c:
        c.execute(query, params)
        keys = tuple([col[0] for col in c.description])

        # We use standard dict here rather than OrderedDict on the assumption
        # that the extra overhead of maintaining ordering over a long list
        # would outweigh the legibility improvement
        return [dict(zip(keys, r)) for r in c]

