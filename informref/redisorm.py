import json

UNDEFINED = object()

class NotUnique(Exception):
    def __init__(self, other, field, value):
        super(NotUnique, self).__init__("%r is not a unique value for '%s'" %
                                        (value, field))
        self.other = other
        self.field = field
        self.value = value
        
        
class MissingRequiredField(Exception):
    pass


class HashField(object):
    """ Descriptor for making redis hash fields look like attributes. """

    def __init__(self, **kw):
        self.name = kw.pop('name', UNDEFINED)
        self.type = kw.pop('type', unicode)
        self.nullable = kw.pop('nullable', True)
        self._unique = kw.pop('_unique', False)
        self.default = kw.pop('default', UNDEFINED)
        self._encode = kw.pop('encode', json.dumps)
        self._decode = kw.pop('encode', json.loads)

    def unique(self, hashobj):
        print hashobj.__dict__
        return self._unique(hashobj.__dict__[self.name])

    def __get__(self, hashobj, hashtype):
        if hashobj is None:
            return self
        assert self.name is not UNDEFINED
        val = hashobj.__dict__.get(self.name, UNDEFINED)
        if val is UNDEFINED:
            raise AttributeError(self.name)
        return hashobj.__dict__[self.name]

    def __set__(self, obj, val):
        assert val is not None
        assert self.name is not UNDEFINED
        if not self.nullable and val is None:
            raise ValueError("'%s' is not nullable" % self.name)
        val = self.type(val)
        encoded = self.encode(val)
        obj.__dict__.setdefault('_dirty', {})[self.name] = encoded
        obj.__dict__[self.name] = val

    def encode(self, value):
        if value is None:
            return None
        return self._encode(self.type(value))

    def decode(self, encoded):
        if encoded is None:
            return encoded
        return self.type(self._decode(encoded))


class Hash(object):

    sep = ':'
    namespace = ()

    def __new__(cls, key, *args, **kw):

        fields = cls.fields().items()

        for name, field in fields:
            if field.name is UNDEFINED:
                field.name = name

        hashobj = super(Hash, cls).__new__(cls, *args)
        hashobj.__key__ = key

        for name, field in fields:
            value = kw.pop(name, field.default)
            if value is not UNDEFINED:
                setattr(hashobj, name, value)
            elif not field.nullable:
                raise MissingRequiredField("value for '%s' is required" % field.name)

        if kw:
            raise TypeError('unexpected keyword arguments %r' % kw.keys())

        return hashobj
   
    @staticmethod 
    def field(*args, **kwargs):
        return HashField(*args, **kwargs)
    
    @property
    def key(self):
        return self.__key__

    @property
    def seq(self):
        return int(self.key.rpartition(self.__class__.sep)[2])

    @classmethod
    def relkey(cls, *parts):
        return cls.sep.join(cls.namespace + tuple(str(p) for p in parts))

    @classmethod
    def create(cls, redis_client, **kw):
        seq = redis_client.incr(cls.relkey('seq'))
        instance = cls(cls.relkey(seq), **kw)

        pipe = redis_client.pipeline()
        uniques = []
        for name, field in cls.fields().items():
            if field.unique:
                unique_key = cls.relkey('unique', field.name)
                unique_value = getattr(instance, field.name, UNDEFINED)
                if unique_value is UNDEFINED:
                    continue
                if isinstance(unique_value, basestring):
                    unique_value = unique_value.lower()
                pipe.watch(unique_key)
                score = redis_client.zscore(unique_key, unique_value)
                if score is not None:
                    other = cls.relkey(int(score))
                    raise NotUnique(other, field.name, unique_value)
                uniques.append((unique_key, unique_value))

        pipe.multi()
        try:
            # give our unit tests a chance to break a watch
            _test_watch_hook(instance.__key__)
            for key, value in uniques:
                pipe.zadd(key, value, seq)
            instance.hmset(pipe, instance.__key__)
            pipe.execute()
        finally:
            pipe.reset()
        return instance

    @classmethod
    def fields(cls):
        return {k: v for k, v in cls.__dict__.items() if isinstance(v, HashField)}

    @classmethod
    def hmget(cls, redis, key):
        fields = cls.fields()
        names = fields.keys()
        values = redis.hmget(key, names)
        decoded = {n: fields[n].decode(v) for n, v in zip(names, values) if v is not None}
        return cls(key, **decoded)

    def hmset(self, redis, key):
        dirty = self.__dict__.pop('_dirty', {})
        if dirty:
            redis.hmset(key, dirty)


# used for testing
def _test_watch(instance_key):
    pass

_test_watch_hook = _test_watch
