#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""All websocket routes and functions"""
from cherrydoor import socket, emit, dt, mongo, current_user, disconnect
import functools

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)

    return wrapped


@socket.on("stats", namespace="/api")
@authenticated_only
def stats(json):
    try:
        time_from = dt.datetime.fromisoformat(json["time_from"])
    except KeyError:
        time_from = dt.date.today() - dt.timedelta(days=7)
    try:
        time_to = dt.datetime.fromisoformat(json["time_to"])
    except KeyError:
        time_to = dt.datetime.now()

    results = mongo.logs.find(
        {"timestamp": {"$lt": time_to, "$gte": time_from}},
        {"timestamp": 1, "_id": 1, "cid": 0},
    )
    emit("stats", results)
    return results


@socket.on("get_user", namespace="/api")
@authenticated_only
def get_user(json):
    try:
        username = json["username"]
        user = mongo.users.find_one({"name": username}, {"password": 0})
        if not user:
            raise KeyError
    except KeyError:
        try:
            card = json["card"]
            user = mongo.users.find_one({"cards": card}, {"password": 0})
            if not user:
                raise KeyError
        except KeyError:
            return False
    emit("user", user)
    return user
