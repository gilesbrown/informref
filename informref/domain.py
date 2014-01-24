from __future__ import unicode_literals
import re
from codecs import getreader
from contextlib import closing
from urlparse import urlsplit
from pkg_resources import resource_stream


class DomainError(Exception):
    """Base class for errors in domain name."""

class UnrecognizedTopLevelDomain(Exception):
    """Raised when the top-level domain has not been recognized."""


class EmptySecondLevelDomain(Exception):
    """Raised when the second level domain is empty."""


def _tld_names():
    with closing(resource_stream(__name__, 'effective_tld_names.dat')) as stream:
        for line in getreader('utf-8')(stream):
            name = line.strip()
            if not name or name.startswith('//') or name.startswith('!'):
                continue
            yield name.replace('.', '\.').replace('*\.', '[^.]+\.')


_tld_re = re.compile('\.({})$'.format('|'.join(sorted(_tld_names(),
                                                      key=len, reverse=True))))


def second_level_domain(uri):

    parts = urlsplit(uri)
    if parts.scheme:
        hostname = parts.hostname
    else:
        hostname = uri.partition('/')[0]

    # prefixing with '.' helps us catch case where netloc is a tld name
    match = _tld_re.search('.' + hostname)
    if match is None:
        raise UnrecognizedTopLevelDomain(uri)

    tld = match.group(0)
    next_level = hostname[:-len(tld)].rpartition('.')[2].strip()
    if not next_level:
        raise EmptySecondLevelDomain(uri)

    return next_level + tld


if __name__ == '__main__':
    # Allows an easy command line check
    import sys
    for uri in sys.argv[1:]:
        print '%s=%s' % (uri, second_level_domain(uri))
