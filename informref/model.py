""" A very simple model stored in redis. """

import os

import redis
from simpleflake import simpleflake
from itertools import chain
from .redishash import Hash, HashField


redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis_client = redis.from_url(redis_url)

num_create_retries = 7
FINAL = object()
UNDEFINED = object()

class normalized(unicode):
    def __new__(cls, string, *args):
        string = u' '.join(string.split())
        return unicode.__new__(cls, string, *args)


class Retailer(Hash):
    incomplete = HashField(type=bool, default=True)
    name = HashField(type=normalized)


def create_retailer(**kw):
    for attempt in chain(xrange(num_create_retries), (FINAL,)):
        try:
            return attempt_create_retailer(**kw)
        except redis.WatchError:
            if attempt is FINAL:
                raise


def get_retailer(flake):
    flake = int(flake)
    retailer = Retailer.hmget(redis_client, format_retailer_key(flake))
    retailer.flake = flake
    if hasattr(retailer, 'name'):
        # every retailer must have a name
        return retailer


def delete_retailer(flake):
    retailer = get_retailer(flake)
    pipe = redis_client.pipeline()
    pipe.multi()
    try:
        if hasattr(retailer, 'name'):
            pipe.delete(format_name_key(retailer.name))
        pipe.delete(format_retailer_key(retailer.flake))
        pipe.execute()
    finally:
        pipe.reset()


def find_retailer_by_name(name):
    flake = redis_client.get(format_name_key(name))
    if flake is not None:
        return get_retailer(flake)


def attempt_create_retailer(name=None):

    pipe = redis_client.pipeline()
    try:

        retailer = Retailer(incomplete=True)

        if name is not None:
            # check name is not already used
            retailer.name = name
            retailer.incomplete = False
            name_key = format_name_key(retailer.name)
            pipe.watch(name_key)
            other_flake = pipe.get(name_key)
            if other_flake is not None:
                raise RetailerNameInUse(other_flake)
        else:
            name_key = None

        # allocate a unique id
        flake = simpleflake()
        retailer_key = format_retailer_key(flake)
        pipe.watch(retailer_key)

        pipe.multi()
        # give our unit tests a chance to break a watch
        _test_watch_hook(flake)
        if name_key:
            pipe.set(name_key, flake)
        retailer.hmset(pipe, retailer_key)
        pipe.execute()

        retailer.flake = flake

        return retailer

    finally:
        pipe.reset()


class RetailerNameInUse(Exception):
    """ Raised when retailer name is already in use. """
    def __init__(self, other_flake):
        super(RetailerNameInUse, self).__init__(other_flake)
        self.other = int(other_flake)


def format_name_key(name):
    return u'retailer.name.key:{0}'.format(normalized(name).lower())


format_retailer_key = u'retailer:{0}'.format

# used for testing
def _test_watch(flake):
    pass
_test_watch_hook = _test_watch
