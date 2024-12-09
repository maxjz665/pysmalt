"""
Обработчики всех запросов к серверу
"""
import re
from functools import reduce
from operator import add
from time import time

from django.db import connection


def stats_middleware(get_response):
    """
    In your base template, put this:
    <div id="stats">
    <!-- STATS: Total: %(total_time).2fs Python: %(python_time).2fs DB: %(db_time).2fs Queries: %(db_queries)d ENDSTATS -->
    </div>
    """

    def middleware(request):

        # Uncomment the following if you want to get stats on DEBUG=True only
        # if not settings.DEBUG:
        #    return None

        # get number of db queries before we do anything
        n = len(connection.queries)

        # time the view
        start = time()
        response = get_response(request)
        total_time = time() - start

        # compute the db time for the queries just run
        db_queries = len(connection.queries) - n
        if db_queries:
            db_time = reduce(add, [float(q['time'])
                                   for q in connection.queries[n:]])
        else:
            db_time = 0.0

        # and backout python time
        python_time = total_time - db_time

        stats = {
            'total_time': total_time,
            'python_time': python_time,
            'db_time': db_time,
            'db_queries': db_queries,
        }

        # replace the comment if found
        if response:
            try:
                # detects TemplateResponse which are not yet rendered
                if response.is_rendered:
                    rendered_content = response.content
                else:
                    rendered_content = response.rendered_content
            except AttributeError:  # django < 1.5
                rendered_content = response.content
            if rendered_content:
                s = rendered_content.decode('utf-8')
                regexp = re.compile(
                    r'(?P<cmt><!--\s*STATS:(?P<fmt>.*?)ENDSTATS\s*-->)'
                )
                match = regexp.search(s)
                if match:
                    s = (s[:match.start('cmt')] +
                         match.group('fmt') % stats +
                         s[match.end('cmt'):])
                    response.content = s

        return response

    return middleware
