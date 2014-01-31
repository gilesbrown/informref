import redis
from nose.tools import with_setup, eq_, ok_, raises
from informref import model, redishash

# We need another client to test WATCH and retries
other_client = redis.from_url(model.redis_url)

ex_name = 'Big Box'
ex_same_name = '    big    box    '

def setup():
    model.num_create_retries = 0
    redishash._test_watch_hook = redishash._test_watch
    model.redis_client.flushdb()

seq_key = model.Retailer.relkey('seq')
unique_name_key = model.Retailer.relkey('unique', 'name')

def check_keys(expected):
    eq_(set(model.redis_client.keys()), set(expected))


@with_setup(setup)
def test_create_retailer():
    retailer = model.create_retailer(name='ex_name')
    check_keys([retailer.key, seq_key, unique_name_key])


@raises(TypeError)
@with_setup(setup)
def test_create_retailer_with_no_name():
    model.create_retailer()


@with_setup(setup)
def test_create_retailer_with_same_name():
    retailer1 = model.create_retailer(name=ex_name)
    try:
        # name gets normalized to same as above
        model.create_retailer(name=ex_same_name)
        ok_(False, "we should not get here")
    except redishash.NotUnique as exc:
        eq_(exc.other, retailer1.key)
    check_keys([retailer1.key, seq_key, unique_name_key])


class BreakWatch(object):

    def __init__(self, max_calls=1):
        self.num_calls = 0
        # Stop breaking after this many calls
        self.max_calls = max_calls

    def __call__(self, flake):
        if self.num_calls < self.max_calls:
            self.break_watch(flake)
        self.num_calls += 1

    def break_watch(self, flake):
        other_client.hset(model.format_retailer_key(flake), 'incomplete', 'false')


@with_setup(setup)
def test_create_retailer_retry_succeeds():
    model._test_watch_hook = BreakWatch()
    model.num_create_retries = 1
    model.create_retailer(name=ex_name)


@raises(redis.WatchError)
@with_setup(setup)
def test_create_retailer_watch_error_name():
    class BreakNameWatch(BreakWatch):
        def break_watch(self, flake):
            assert other_client.zadd(unique_name_key, 'anything', 666)
    redishash._test_watch_hook = BreakNameWatch()
    model.create_retailer(name=ex_name)


@with_setup(setup)
def test_get_retailer():
    retailer = model.create_retailer(name=ex_name)
    retailer = model.get_retailer(retailer.seq)
    eq_(retailer.name, ex_name)


@with_setup(setup)
def test_delete_retailer():
    retailer = model.create_retailer(name=ex_name)
    model.delete_retailer(retailer.seq)
    check_keys([seq_key, unique_name_key])


@with_setup(setup)
def test_find_retailer_by_name():
    created = model.create_retailer(name=ex_name)
    found = model.find_retailer_by_name(name=ex_name)
    eq_(created.key, found.key)
