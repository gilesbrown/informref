import redis
from nose.tools import with_setup, eq_, ok_, raises
from informref import model

# We need another client to test WATCH and retries
other_client = redis.from_url(model.redis_url)

ex_name = 'Big Box'
ex_same_name = '    big    box    '

def setup():
    model.num_create_retries = 0
    model._test_watch_hook = model._test_watch
    model.redis_client.flushdb()


def check_keys(expected):
    eq_(set(model.redis_client.keys()), set(expected))


@with_setup(setup)
def test_create_retailer():
    flake = model.create_retailer()
    check_keys([model.format_retailer_key(flake)])


@with_setup(setup)
def test_create_retailer_with_name():
    flake = model.create_retailer(name=ex_name)
    check_keys([model.format_retailer_key(flake), model.format_name_key(ex_name)])


@with_setup(setup)
def test_create_retailer_with_same_name():
    flake1 = model.create_retailer(name=ex_name)
    try:
        # name gets normalized to same as above
        model.create_retailer(name=ex_same_name)
        ok_(False, "we should ever get here")
    except model.RetailerNameInUse as exc:
        eq_(exc.other, flake1)
    check_keys([model.format_retailer_key(flake1), model.format_name_key(ex_name)])


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


@raises(redis.WatchError)
@with_setup(setup)
def test_create_retailer_watch_error():
    model._test_watch_hook = BreakWatch()
    model.create_retailer(name=ex_name)


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
            other_flake = model.simpleflake()
            other_client.set(model.format_name_key(ex_same_name), other_flake)
    model._test_watch_hook = BreakNameWatch()
    model.create_retailer(name=ex_name)


@with_setup(setup)
def test_get_retailer():
    flake = model.create_retailer(name=ex_name)
    retailer = model.get_retailer(flake)
    eq_(retailer.name, ex_name)


@with_setup(setup)
def test_delete_retailer():
    flake = model.create_retailer()
    model.delete_retailer(flake)
    check_keys([])


@with_setup(setup)
def test_delete_retailer_with_name():
    flake = model.create_retailer(name=ex_name)
    model.delete_retailer(flake)
    check_keys([])

