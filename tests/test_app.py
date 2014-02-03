from collections import OrderedDict
from nose.tools import eq_, ok_, with_setup
from werkzeug.datastructures import MultiDict
from informref.app import app
from informref.model import redis_client
import inform

ex_name = "Good Stuff"
ex_same_name = " good stuff "


class FlaskTestSession(object):
    def __init__(self):
        self.test_client = app.test_client()
    def request(self, method, url, params=None, data=None, headers=None):
        
        if data is not None:
            # Flask test client wants to call .iteritems() on this...
            data = MultiDict(data)
            
        res = self.test_client.open(url, method=method, query_string=params, 
                                    data=data, headers=headers, follow_redirects=True)
        res.url = url
        res.content = res.data
        return res


def setup():
    inform.session_factory = FlaskTestSession
    redis_client.flushdb()


def v1():
    v1 = inform.get('/').select_version()
    #ok_(v1.response.url.endswith('/v1'))
    print v1.response.url
    return v1


@with_setup(setup)
def test_create_retailer():
    res = v1().create_retailer(name="Baker's Dozen")
    eq_(res.response.status_code, 201)
#     resp_post = client.post('/retailer/', data=data)
#     eq_(resp_post.status_code, 201)
#     data = dict(name=ex_same_name)
#     resp_post = client.post('/retailer/', data=data)
#     eq_(resp_post.status_code, 303)
#     resp_get = client.get(resp_post.location)
#     eq_(resp_get.status_code, 200)

#     print resp_get.data