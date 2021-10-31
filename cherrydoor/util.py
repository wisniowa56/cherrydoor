"""Just some utility functions."""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import datetime as dt
from typing import Union

from aiohttp import web


def redirect(router, route_name):
    """Retrun a redirect to a specified route (by name).

    Paremeters
    ----------
    route_name : str
        The name of the route to redirect to.
    Returns
    -------
    web.Response
        The redirect response or HTTPNotFound if the route does not exist.
    """
    try:
        location = router.get(route_name, {}).url_for()
        return web.HTTPFound(location)
    except AttributeError:
        return web.HTTPNotFound()


def round_time(dt_input=None, dateDelta=dt.timedelta(minutes=1)):
    """Round a datetime object to a multiple of a timedelta.

    Paremeters
    ----------
    dt_input : datetime.datetime
        The datetime object to round.
    dateDelta : datetime.timedelta, default=datetime.timedelta(minutes=1)
        The timedelta object to round to.
    Returns
    -------
    datetime.datetime
        The datetime object rounded to the nearest dateDelta.

    Notes
    -----
    Originally by:
        - Terry Husson 2012: Use it as you want but don't blame me.
        - Stijn Nevens 2014: Changed to use only datetime objects as variables
    """
    roundTo = dateDelta.total_seconds()

    if dt_input is None:
        dt_input = dt.datetime.now()
    seconds = (dt_input - dt_input.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt_input + dt.timedelta(0, rounding - seconds, -dt_input.microsecond)


# pylint: disable=unsubscriptable-object
def get_datetime(time: Union[int, str], default=None):
    """Convert a timestamp or isoformat string to a datetime object.

    Parameters
    ----------
    time : int or str
        The timestamp or string to convert.
    default : datetime.datetime, optional
        The default datetime object to return if time can't be converted.
    Returns
    -------
    datetime.datetime
        The datetime object.
    """
    if isinstance(time, int) or time.isnumeric():
        return dt.datetime.fromtimestamp(int(time))
    if time != "":
        return dt.datetime.fromisoformat(time)
    return default


async def aenumerate(sequence, start=0):
    """Asynchronously enumerate an iterator from a given start value.

    Paremeters
    ----------
    sequence : iterable
        The sequence to enumerate.
    start : int, default=0
        The starting value to start enumeration.
    """
    n = start
    for elem in sequence:
        yield n, elem
        n += 1
