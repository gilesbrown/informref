""" Mapping of redis to objects. """

import json
from itertools import islice, izip_longest, tee



UNDEFINED = object()


class ConstraintError(Exception):
    pass



def n_wise(iterable, n):
    n_iterators = tee(iterable, n)
    zippables = (islice(it, j, None, n) for j, it in enumerate(n_iterators))
    return izip_longest(*zippables)


class NotUnique(ConstraintError):
    def __init__(self, value, name, id, hashcls):
        msg = "instance %d of %s is already using %r for field '%s'" % (
            id, hashcls, value, name,
        )
        ConstraintError.__init__(self, msg)
        self.hashcls = hashcls
        self.id = id
        self.name = name
        self.value = value


class HashField(object):
    """ Descriptor for making redis hash fields look like attributes. """

    def __init__(self, **kw):
        self.name = kw.pop('name', UNDEFINED)
        self.type = kw.pop('type', unicode)
        self.nullable = kw.pop('nullable', True)
        self.unique = kw.pop('unique', False)
        if self.unique and not hasattr(self.unique, '__call__'):
            self.unique = unicode
        self.default = kw.pop('default', UNDEFINED)
        self._encode = kw.pop('encode', json.dumps)
        self._decode = kw.pop('encode', json.loads)

    def check_unique(self, hashobj, redis, pipe=None):

        value = self.unique_value(hashobj)
        if value is UNDEFINED:
            return

        key = hashobj.__class__.relative_key('unique', self.name)

        if pipe is not None:
            pipe.watch(key)

        score = redis.zscore(key, value)
        if score is None:
            return

        id = int(score)
        if id == hashobj.id:
            return

        raise NotUnique(value, self.name, id, hashobj.__class__)

    def set_unique(self, hashobj, redis, pipe):
        value = self.unique_value(hashobj)
        if value is not UNDEFINED:
            key = hashobj.__class__.relative_key('unique', self.name)
            self.delete_unique(hashobj, redis, pipe)
            pipe.zadd(key, value, hashobj.id)

    def delete_unique(self, hashobj, redis, pipe):
        key = hashobj.__class__.relative_key('unique', self.name)
        pipe.zremrangebyscore(key, hashobj.id, hashobj.id)

    def unique_value(self, hashobj):

        if not self.unique:
            return UNDEFINED

        value = getattr(hashobj, self.name, UNDEFINED)
        if value is not UNDEFINED:
            if hasattr(self.unique, '__call__'):
                value = self.unique(value)
            else:
                value = value
            return value

        return UNDEFINED

    def __get__(self, hashobj, hashtype):
        if hashobj is None:
            return self
        assert self.name is not UNDEFINED
        val = hashobj.__dict__.get(self.name, UNDEFINED)
        if val is UNDEFINED:
            raise AttributeError(self.name)
        return hashobj.__dict__[self.name]

    def __set__(self, obj, value):
        if not self.nullable and value is None:
            raise ValueError("'%s' is not nullable" % self.name)
        value = self.type(value)
        encoded = self.encode(value)
        obj.__dict__.setdefault('_dirty', {})[self.name] = encoded
        obj.__dict__[self.name] = value

    def encode(self, value):
        if value is None:
            return None
        return self._encode(self.type(value))

    def decode(self, encoded):
        if encoded is None:
            return encoded
        return self.type(self._decode(encoded))


class HashWithFields(type):
    def __new__(mcs, name, bases, clsdict):
        fields = {}
        for k, v in clsdict.items():
            if isinstance(v, HashField):
                v.name = k
                fields[k] = v
        clsdict['__fields__'] = fields
        return super(HashWithFields, mcs).__new__(mcs, name, bases, clsdict)

class Hash(object):

    __metaclass__ = HashWithFields
    #__metaclass__ = HashFields

    sep = ':'

    def __init__(self, id=None, **kw):
        super(Hash, self).__init__()
        if id is None:
            raise ValueError
        self.id = id
        for k, v in kw.items():
            if not k in self.__fields__:
                raise TypeError('unexpected keyword argument %r' % k)
            setattr(self, k, v)

    @classmethod
    def relative_key(cls, *parts):
        namespace = (getattr(cls, '__namespace__', cls.__name__.lower()),)
        return cls.sep.join(namespace + tuple(str(p) for p in parts))

    @classmethod
    def create(cls, redis, **kw):
        id = redis.incr(cls.relative_key('incr'))
        instance = cls(id, **kw)
        instance.hmset(redis)
        return instance

    @classmethod
    def get(cls, redis, id):
        names = cls.__fields__.keys()
        hash_key = cls.relative_key(id)
        ids_key = cls.relative_key('ids')
        values = redis.hmget(hash_key, names)
        if not redis.sismember(ids_key, id):
            return None
        decoded = {n: cls.__fields__[n].decode(v) for n, v in zip(names, values) if v is not None}
        return cls(id, **decoded)

    def hmset(self, redis):

        assert self.id is not None

        pipe = redis.pipeline()
        for field in self.__fields__.values():
            if field.unique:
                field.check_unique(self, redis, pipe)

        hash_key = self.__class__.relative_key(self.id)
        ids_key = self.__class__.relative_key('ids')

        pipe.watch(hash_key)

        dirty = self.__dict__.pop('_dirty', {})

        try:
            pipe.multi()
            _test_watch_hook(self)
            if dirty:
                pipe.hmset(hash_key, dirty)
            for field in self.__fields__.values():
                if field.unique:
                    field.set_unique(self, redis, pipe)
            pipe.sadd(ids_key, self.id)
            pipe.execute()

        finally:
            pipe.reset()

    def delete(self, redis):

        assert self.id is not None

        pipe = redis.pipeline()
        hash_key = self.__class__.relative_key(self.id)
        ids_key = self.__class__.relative_key('ids')

        pipe.watch(hash_key)

        try:
            pipe.multi()
            _test_watch_hook(self)
            pipe.delete(hash_key)
            for field in self.__fields__.values():
                if field.unique:
                    field.delete_unique(self, redis, pipe)
            pipe.srem(ids_key, self.id)
            pipe.execute()

        finally:
            pipe.reset()

    @classmethod
    def sort(cls, redis, by=None, get=None):
        get_list = ['#']
        ids_key = cls.relative_key('ids')
        if get is None:
            get_fields = cls.__fields__.values()


        get_list.extend((cls.relative_key('*->{0.name}'.format(f))
                         for f in get_fields))

        instances = []
        for row in n_wise(redis.sort(ids_key, get=get_list), n=len(get_list)):
            kw = {}
            for field, value in zip(get_fields, row[1:]):
                kw[field.name] = field.decode(value)
            instances.append(cls(int(row[0]), **kw))

        return instances





def _do_nothing(instance):
    pass

# used for testing
_test_watch_hook = _do_nothing
