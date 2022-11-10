import re

from .profiler import SessionProfiler
from .reporters import Reporter, StreamReporter


class EasyProfileMiddleware(object):
    """This middleware prints the number of database queries for each HTTP
    request and can be applied as a WSGI server middleware.

    :param app: WSGI application server
    :param sqlalchemy.engine.base.Engine engine: sqlalchemy database engine
    :param Reporter reporter: reporter instance
    :param list exclude_path: a list of regex patterns for excluding requests
    :param int min_time: minimal queries duration to logging
    :param int min_query_count: minimal queries count to logging

    """

    def __init__(self,
                 app,
                 engine=None,
                 reporter=None,
                 exclude_path=None,
                 min_time=0,
                 min_query_count=1):

        if reporter:
            if not isinstance(reporter, Reporter):
                raise TypeError("reporter must be inherited from 'Reporter'")
            self.reporter = reporter
        else:
            self.reporter = StreamReporter()

        self.app = app
        self.engine = engine
        self.exclude_path = exclude_path or []
        self.min_time = min_time
        self.min_query_count = min_query_count

    def __call__(self, environ, start_response):
        profiler = SessionProfiler(self.engine)
        path = environ.get("PATH_INFO", "")
        if not self._ignore_request(path):
            method = environ.get("REQUEST_METHOD")
            if method:
                path = "{0} {1}".format(method, path)
            try:
                with profiler:
                    response = self.app(environ, start_response)
            finally:
                self._report_stats(path, profiler.stats)
            return response
        return self.app(environ, start_response)

    def _ignore_request(self, path):
        """Check to see if we should ignore the request."""
        return any(re.match(pattern, path) for pattern in self.exclude_path)

    def _report_stats(self, path, stats):
        if (stats["total"] >= self.min_query_count and
                stats["duration"] >= self.min_time):
            self.reporter.report(path, stats)
