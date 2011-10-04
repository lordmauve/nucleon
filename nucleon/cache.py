"""Memcached support"""

from geventmemcache import Memcache
from functools import wraps


# List of servers to use
SERVERS = [
    # ((ip, port), weight)
    (('127.0.0.1', 11211), 1)
]

cache = Memcache(SERVERS)


def get_cache_key(request, *args, **kwargs):
    return request.path_qs


def cached(expiry=600, cache_key=get_cache_key):
    if callable(cache_key):
        def decorator(view):
            @wraps(view)
            def wrapped(request, *args, **kwargs):
                key = cache_key(request, *args, **kwargs)
                resp = cache.get(key)
                if resp is not None:
                    return resp
                resp = view(request, *args, **kwargs)
                cache.set(key, resp, expiry)
                return resp
            return wrapped
    else:
        def decorator(view):
            @wraps(view)
            def wrapped(request, *args, **kwargs):
                resp = cache.get(cache_key)
                if resp is not None:
                    return resp
                resp = view(request, *args, **kwargs)
                cache.set(cache_key, resp, expiry)
                return resp
            return wrapped
    return decorator
