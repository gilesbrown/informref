import json


UNDEFINED = object()
MISSING = object()


class HashField(object):
    """ Descriptor for making redis hash fields look like attributes. """

    def __init__(self, **kw):
        self.name = kw.pop('name', UNDEFINED)
        self.type = kw.pop('type', unicode)
        self.nullable = kw.pop('nullable', True)
        self.default = kw.pop('default', MISSING)

    def __get__(self, hashobj, hashtype):
        if hashobj is None:
            return self
        assert self.name is not UNDEFINED
        val = hashobj.__dict__.get(self.name, MISSING)
        if val is MISSING:
            hashobj.hmget()
        return hashobj.__dict__[self.name]

    def __set__(self, obj, val):
        assert self.name is not UNDEFINED
        if not self.nullable and val is None:
            raise ValueError("'%s' is not nullable" % self.name)
        encoded = self.encode(val)
        obj.__dict__.setdefault('_dirty', {})[self.name] = encoded
        obj.__dict__[self.name] = val

    def encode(self, value):
        if value is None:
            return None
        return json.dumps(self.type(value))

    def decode(self, value):
        if value is None:
            return None
        return self.type(json.loads(value))


class Hash(object):

    def __new__(cls, *args):

        for name, field in cls.fields():
            if field.name is UNDEFINED:
                field.name = name

        hashobj = object.__new__(cls, *args)

        for name, field in cls.fields():
            if field.default is not UNDEFINED:
                setattr(hashobj, name, field.default)

        return hashobj

    def watch(self):
        self.redis.watch(self.key)

    @classmethod
    def fields(cls):
        for name, value in cls.__dict__.items():
            if isinstance(value, HashField):
                yield name, value

    def __enter__(self):
        self.__dict__.setdefault('_dirty', {})
        return self

    def __exit__(self, *exc_info):
        if any(exc_info):
            return
        self.hmset()

    def hmget(self):
        """ Get all the fields. """
        fields = list(Hash.fields(self))
        res = self.redis.hmget(self.key, [name for name, _ in fields])
        values = {}
        for (name, field), encoded_value in zip(fields, res):
            values[name] = field.decode(encoded_value)
        self.__dict__.update(values)

    def hmset(self):
        """ Set all the fields that have been changed. """
        dirty = self.__dict__.pop('_dirty', None)
        if not dirty:
            return
        self.redis.hmset(self.key, dirty)
