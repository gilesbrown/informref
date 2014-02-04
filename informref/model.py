""" A very simple model stored in redis. """

import os

import redis
from operator import methodcaller
from collections import OrderedDict
from itertools import chain
from .redisobjects import Hash, HashField


redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis_client = redis.from_url(redis_url)

num_create_retries = 7
FINAL = object()
UNDEFINED = object()

lowercase = methodcaller('lower')

class normalize_space(unicode):
    def __new__(cls, string, *args):
        string = u' '.join(string.split())
        return unicode.__new__(cls, string, *args)


class Retailer(Hash):

    namespace = ('retailer',)
    name = HashField(type=normalize_space, nullable=False, unique=lowercase)

    def dictify(self):
        return {f.name: f.__get__(self) for f in self.__fields__.values()}


def create_retailer(**kw):
    for attempt in chain(xrange(num_create_retries), (FINAL,)):
        try:
            r =Retailer.create(redis_client, **kw)
            print "HGETALL[1]", redis_client.hgetall('retailer:1'), kw
            return r
        except redis.WatchError:
            if attempt is FINAL:
                raise


def get_retailer(seq):
    retailer = Retailer.hmget(redis_client, Retailer.relkey(seq))
    if hasattr(retailer, 'name'):
        # every retailer must have a name
        return retailer


def delete_retailer(seq):
    retailer = get_retailer(seq)
    pipe = redis_client.pipeline()
    pipe.multi()
    try:
        #if hasattr(retailer, 'name'):
        #    pipe.delete(format_name_key(retailer.name))
        pipe.delete(retailer.key)
        pipe.execute()
    finally:
        pipe.reset()


def find_retailer_by_name(name):
    unique_name_key = Retailer.relkey('unique', 'name')
    score = redis_client.zscore(unique_name_key, normalize_space(name).lower())
    if score is not None:
        return get_retailer(int(score))


def retailer_index():
    print "HGETALL[1]", redis_client.hgetall('retailer:1')
    return [r.dictify() for r in Retailer.sort(redis_client)]


format_retailer_key = u'retailer:{0}'.format
