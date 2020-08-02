#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""All websocket routes and functions"""
import functools
from bson import json_util
import json as jsn
from cherrydoor.server import socket, emit, dt, db, current_user, disconnect

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b0"
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
def stats(json={}):
    try:
        time_from = dt.datetime.fromisoformat(json["time_from"].replace("Z", ""))
    except KeyError:
        time_from = dt.datetime.today() - dt.timedelta(days=7)
    try:
        time_to = dt.datetime.fromisoformat(json["time_to"].replace("Z", ""))
    except KeyError:
        time_to = dt.datetime.now()

    results = db.logs.find(
        {"timestamp": {"$lt": time_to, "$gte": time_from}}, {"card": 0, "_id": 0}
    )
    json_results = [jsn.dumps(doc, default=json_util.default) for doc in results]
    emit("stats", json_results, namespace="/api")
    return json_results


@socket.on("user", namespace="/api")
@authenticated_only
def user(json={}):
    try:
        username = json["username"]
        user = db.users.find_one({"username": username}, {"password": 0, "_id": 0})
        if not user:
            raise KeyError
    except KeyError:
        try:
            card = json["card"]
            user = db.users.find_one({"cards": card}, {"password": 0, "_id": 0})
            if not user:
                raise KeyError
        except KeyError:
            return False
    try:
        if json["edit"]:
            db.users.update_one(user, json["changes"])
    except KeyError:
        pass
    emit("user", user)
    return user


@socket.on("users", namespace="/api")
@authenticated_only
def users():
    try:
        users = db.users.find({}, {"password": 0, "_id": 0})
        json_results = [jsn.dumps(doc, default=json_util.default) for doc in users]
    except:
        return False
    emit("users", json_results)
    return json_results


@socket.on("break_times", namespace="/api")
@authenticated_only
def break_times(json=[]):
    if isinstance(json, list) and len(json) != 0 and isinstance(json[0], list):
        if not any(json[0]):
            db.settings.update(
                {"setting": "break_times"},
                {"setting": "break_times", "value": []},
                upsert=True,
            )
            return_breaks = []
        else:
            try:
                breaks = [
                    [
                        dt.datetime.fromisoformat(item[0].replace("Z", "")).replace(
                            year=2020, month=2, day=2
                        ),
                        dt.datetime.fromisoformat(item[1].replace("Z", "")).replace(
                            year=2020, month=2, day=2
                        ),
                    ]
                    for item in json
                ]
            except IndexError:
                return None
            db_breaks = [{"from": item[0], "to": item[1]} for item in breaks]
            db.settings.update(
                {"setting": "break_times"}, {"$set": {"value": db_breaks}}, upsert=True
            )
            breaks = [
                [item[0].isoformat() + "Z", item[1].isoformat() + "Z"]
                for item in breaks
            ]
            return_breaks = jsn.dumps(breaks, indent=4, sort_keys=True, default=str)
        emit("break_times", return_breaks)
        return return_breaks
    try:
        breaks = list(db.settings.find_one({"setting": "break_times"})["value"])
        breaks = [
            [item["from"].isoformat() + "Z", item["to"].isoformat() + "Z"]
            for item in breaks
        ]
        return_breaks = jsn.dumps(breaks, indent=4, sort_keys=True, default=str)
    except KeyError:
        return None
    emit("break_times", return_breaks)
    return return_breaks
