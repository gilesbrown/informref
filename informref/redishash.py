import json

UNDEFINED = object()


class HashField(object):
    """ Descriptor for making redis hash fields look like attributes. """

    def __init__(self, **kw):
        self.name = kw.pop('name', UNDEFINED)
        self.type = kw.pop('type', unicode)
        self.nullable = kw.pop('nullable', True)
        self.default = kw.pop('default', UNDEFINED)
        self._encode = kw.pop('encode', json.dumps)
        self._decode = kw.pop('encode', json.loads)

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

    def __new__(cls, *args, **kw):

        fields = cls.fields().items()

        for name, field in fields:
            if field.name is UNDEFINED:
                field.name = name

        hashobj = super(Hash, cls).__new__(cls, *args)

        for name, field in fields:
            value = kw.pop(name, field.default)
            if value is not UNDEFINED:
                setattr(hashobj, name, value)

        if kw:
            raise TypeError('unexpected keyword arguments %r' % kw.keys())

        return hashobj

    @classmethod
    def fields(cls):
        return {k: v for k, v in cls.__dict__.items() if isinstance(v, HashField)}

    @classmethod
    def hmget(cls, redis, key):
        fields = cls.fields()
        names = fields.keys()
        values = redis.hmget(key, names)
        decoded = {n: fields[n].decode(v) for n, v in zip(names, values) if v is not None}
        return cls(**decoded)

    def hmset(self, redis, key):
        dirty = self.__dict__.pop('_dirty', {})
        if dirty:
            redis.hmset(key, dirty)
