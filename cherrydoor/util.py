"""
Just some utility functions
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import datetime as dt

from aiohttp import web


def redirect(router, route_name):
    """Retrun a redirect to a specified route (by name)"""
    try:
        location = router.get(route_name, {}).url_for()
        return web.HTTPFound(location)
    except AttributeError:
        return web.HTTPNotFound()


def round_time(dt_input=None, dateDelta=dt.timedelta(minutes=1)):
    """Round a datetime object to a multiple of a timedelta
    dt_input : datetime.datetime object, default now.
    dateDelta : timedelta object, we round to a multiple of this, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
            Stijn Nevens 2014 - Changed to use only datetime objects as variables
    """
    roundTo = dateDelta.total_seconds()

    if dt_input == None:
        dt_input = dt.datetime.now()
    seconds = (dt_input - dt_input.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt_input + dt.timedelta(0, rounding - seconds, -dt_input.microsecond)


def get_datetime(time, default):
    if isinstance(time, int) or time.isnumeric():
        return dt.datetime.fromtimestamp(int(time))
    elif time != "":
        return dt.datetime.fromisoformat(time)
    else:
        return default


async def aenumerate(sequence, start=0):
    """Asynchronously enumerate an iterator from a given start value"""
    n = start
    for elem in sequence:
        yield n, elem
        n += 1
