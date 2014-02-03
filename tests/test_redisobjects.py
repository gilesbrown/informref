import os
import sys
import re
from functools import wraps
from collections import defaultdict
from operator import methodcaller
import redis as redismodule
from nose.tools import eq_, ok_, with_setup

from redisobjects import Hash, HashField, NotUnique

redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
redis = redismodule.from_url(redis_url)

lowercase = methodcaller('lower')


class normalize_space(unicode):
    def __new__(cls, string, *args):
        string = u' '.join(string.split())
        return unicode.__new__(cls, string, *args)
    
def two_uc_letters(abbrev):
    match = re.match('\s*([A-Z]{2,2})$\s*', abbrev, re.I)
    if match is None:
        raise ValueError(abbrev)
    return match.group(1).upper()

#class City(Hash):
#    state = State
#    name = HashField(type=normalize_space, nullable=False, unique=lowercase)
#    population = HashField(type=int)
    
class State(Hash):
    name = HashField(type=normalize_space, nullable=False, unique=lowercase)
    abbreviation = HashField(type=two_uc_letters, nullable=False)
    #cities = Collection(City)
    


   
def setup(): 
    redis.flushdb()


def check_integrity(sep=':'):
    
    ids = defaultdict(set)
    uniques = defaultdict(lambda : defaultdict(set))
    
    for k in redis.keys():
        print "KEY: %r" % k
        if ':unique:' in k:
            print k, redis.zrange(k, 0, -1, withscores=True)
        head, _, tail = k.rpartition(sep)
        try:
            id = int(tail)
            ids_key = sep.join((head, 'ids'))
            ids[ids_key].add(str(id))
        except ValueError:
            if head.endswith(':unique'):
                for value, id in redis.zrange(k, 0, -1, withscores=True):
                    print "UU:", value, id
                    instance_key = sep.join((head.rpartition(sep)[0], str(int(id))))
                    uniques[instance_key][tail].add(value)
        
    for ids_key, hash_ids in ids.items():
        members = redis.smembers(ids_key)
        # Each 'ids' set should contain exactly the set if hash ids found
        eq_(members, hash_ids)
        
    module = sys.modules[__name__]
    classes = {
        k.lower(): v for k, v in module.__dict__.items() if isinstance(v, type(Hash))
    }
        
    for hash_key, fields in uniques.items():
        print "UNIQUE:", hash_key, fields
        names = fields.keys()
        values = redis.hmget(hash_key, names)
        for name, value in zip(names, values):
            classname = hash_key.rsplit(sep)[-2]
            fieldobj = getattr(classes[classname], name)
            print "CHECK:", fieldobj.unique(fieldobj.decode(value)), fields[name]
            eq_(set([fieldobj.unique(fieldobj.decode(value))]), fields[name])

            
def with_integrity_check(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        finally:
            check_integrity()
    return wrapper

@with_setup(setup)
@with_integrity_check
def test_hash_create():
    state = State.create(redis, name=' California ', abbreviation='ca')
    eq_(state.name, 'California')
    eq_(state.abbreviation, 'CA')


@with_setup(setup)
@with_integrity_check
def test_hash_create_same_name():
    state1 = State.create(redis, name=' California ', abbreviation='ca')
    try:
        state1 = State.create(redis, name=' California ', abbreviation='ca')
        ok_(False)
    except NotUnique as exc:
        eq_(exc.id, 1)
        
     
@with_setup(setup)
@with_integrity_check
def test_hash_update():
    state = State.create(redis, name=' California ', abbreviation='ca')
    state.name = 'Oregon'
    state.hmset(redis)


@with_setup(setup)
@with_integrity_check
def test_hash_hmget():
    created = State.create(redis, name=' California ', abbreviation='ca')
    got = State.get(redis, created.id)
    eq_(created.id, got.id)
    eq_(created.name, got.name)
    eq_(created.abbreviation, got.abbreviation)

    
@with_setup(setup)
@with_integrity_check
def test_hash_delete():
    created = State.create(redis, name=' California ', abbreviation='ca')
    instance = State(created.id)
    instance.delete(redis)
    got = State.get(redis, created.id)
    eq_(got, None)