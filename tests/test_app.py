from nose.tools import eq_, with_setup
from informref.app import app
from informref.model import redis_client

ex_name = "Good Stuff"
ex_same_name = " good stuff "


def setup():
    redis_client.flushdb()


@with_setup(setup)
def test_create_retailer():
    client = app.test_client()
    data = dict(name=ex_name)
    resp_post = client.post('/retailer/', data=data)
    eq_(resp_post.status_code, 201)
    data = dict(name=ex_same_name)
    resp_post = client.post('/retailer/', data=data)
    eq_(resp_post.status_code, 303)
    resp_get = client.get(resp_post.location)
    eq_(resp_get.status_code, 200)
    print resp_get.data
