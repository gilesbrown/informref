from urlparse import urlparse, urlunparse

class Select(object):
    def __init__(self, name, values, selected=None):
        self.name = name
        self.values = values
        if selected is not None and selected < 0:
            selected = len(values) + selected
        self.selected = selected
    def options(self):
        for i, (k, v) in enumerate(self.values):
            yield (k, v, i == self.selected)

class Form(object):
    def __init__(self, id, *fields, **kw):
        self.id = id
        self.fields = fields
        self.action = kw.pop('action', "")
        self.method = kw.pop('method', None)

    @property
    def browser_method(self):
        if self.method not in (None, 'GET'):
            # Anything else is either POST or tunnelled through POST
            return 'POST'
        return self.method

    @property
    def browser_action(self):
        if self.method in (None, 'GET', 'POST'):
            return self.action
        parsed = urlparse(self.action)
        query = '_method={method}{sep}{query}'.format(
            method=self.method,
            sep='&' if parsed.query else '',
            query=parsed.query,
        )
        return urlunparse(parsed._replace(query=query))

def is_form(obj):
    return isinstance(obj, Form)

def is_select(obj):
    return isinstance(obj, Select)

def is_link(obj):
    return isinstance(obj, Link)

class Link(object):
    def __init__(self, href, id=None):
        self.id = id
        self.href = href

class Input(object):
    def __init__(self, name):
        self.name = name

class Value(object):
    def __init__(self, id, value):
        self.id = id
        self.value = value
    def __repr__(self):
        return str(self.value)

inform_jinja_functions = dict(
    is_form=is_form,
    is_select=is_select,
    is_link=is_link
)
