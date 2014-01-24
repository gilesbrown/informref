from nose.tools import eq_
from informref import middleware

methods = ['DELETE', 'PUT']
subn = middleware.methods_subn(['DELETE', 'PUT'])

def test_methods_subn():
    eq_(subn('_method=DELETE'), ('DELETE', ''))


def test_methods_subn_no_match():
    eq_(subn('_method=BODGE'), (None, '_method=BODGE'))


def test_methods_subn_first_parameter():
    eq_(subn('_method=DELETE&x=1'), ('DELETE', 'x=1'))


def test_methods_subn_middle_parameter():
    eq_(subn('x=1&_method=DELETE&y=2'), ('DELETE', 'x=1&y=2'))


def test_methods_subn_last_parameter():
    eq_(subn('x=1&_method=DELETE'), ('DELETE', 'x=1'))
