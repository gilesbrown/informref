import re

def methods_subn(methods):
    sre = re.compile('(^|&)_method=({0})($|&)'.format('|'.join(methods)))
    def subn(query_string):
        methods = []
        def repl(match):
            methods.append(match.group(2))
            return match.group(1) and match.group(3)
        (query_string, n) = sre.subn(repl, query_string, count=1)
        method = methods and methods[0] or None
        return method, query_string
    return subn


class MethodFromParam(object):
    """WSGI middleware for collecting site usage
    """
    def __init__(self, app, methods=['DELETE', 'PATCH']):
        self.app = app
        self.subn = methods_subn(methods)

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        if query_string:
            method, query_string = self.subn(query_string)
            if method:
                environ["REQUEST_METHOD"] = method
                environ["QUERY_STRING"] = query_string
        return self.app(environ, start_response)
