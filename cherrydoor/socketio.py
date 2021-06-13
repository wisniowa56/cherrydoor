"""
Websocket handlers
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import asyncio
import logging
from datetime import datetime as dt

import socketio
from aiohttp_security import check_permission

from aiohttp import web, WSMsgType

from cherrydoor.auth import get_permissions, permissions_available, hasher
from cherrydoor.database import (
    get_users,
    modify_user,
    create_users as create_users_in_db,
    set_default_permissions,
    get_settings,
    save_settings,
    delete_user as delete_user_from_db,
)

logger = logging.getLogger("SOCKET.IO")
internal_logger = logging.getLogger("SOCKET.IO-INTERNALS")
internal_logger.setLevel(logging.ERROR)

sio = socketio.AsyncServer(
    async_mode="aiohttp",
    cors_allowed_origins="*",
    logger=internal_logger,
    engineio_logger=internal_logger,
)


async def authenticate_socket(sid, permission):
    request = sio.get_environ(sid)["aiohttp.request"]
    async with sio.session(sid) as session:
        if not isinstance(session.get("permissions", None), list):
            session["permissions"] = await get_permissions(request)
        if permission not in session.get("permissions", []):
            try:
                await check_permission(request, permission)
                session["permissions"].append(permission)
                return True
            except (web.HTTPUnauthorized, web.HTTPForbidden):
                raise socketio.exceptions.ConnectionRefusedError(
                    f"unauthorized - {permission} permission required"
                )
        else:
            return True


async def setup_socket_tasks(app):
    app["emit_status"] = sio.start_background_task(send_status, app)
    app["emit_serial"] = sio.start_background_task(send_console, app)
    logger.debug("Finished setting up socket.io tasks")


async def send_status(app):
    while True:
        try:
            await sio.emit(
                "door",
                {
                    "open": bool(app["serial"].door_open),
                    "break": bool(app["serial"].is_break),
                },
                room="door",
            )
        except Exception as e:
            logger.debug("failed to emit status. Exception: %s", e)
        await asyncio.sleep(1)


async def send_console(app):
    async with app["db"].terminal.watch(
        pipeline=[
            {
                "$match": {
                    "operationType": {"$in": ["insert", "update", "replace", "rename"]},
                }
            },
            {
                "$project": {
                    "command": "$fullDocument.command",
                    "arguments": "$fullDocument.arguments",
                    "timestamp": {
                        "$dateToString": {
                            "format": "%H:%M:%S:%L",
                            "date": "$fullDocument.timestamp",
                        }
                    },
                }
            },
        ],
        full_document="updateLookup",
    ) as terminal_change_stream:
        async for change in terminal_change_stream:
            try:
                await sio.emit("serial_command", data=change, room="serial_console")
            except Exception as e:
                logger.exception("failed to emit serial result. Exception: %s", e)


async def send_new_logs(app):
    # TODO actually finish this function
    async with app["db"].logs.watch(
        pipeline=[
            {"$match": {"operationType": {"$in": ["insert", "update", "replace"]},}},
            {
                "$project": {
                    "value": "$fullDocument.value",
                    "setting": "$fullDocument.setting",
                }
            },
        ],
        full_document="updateLookup",
    ) as logs_change_stream:
        async for change in logs_change_stream:
            try:
                await sio.emit(
                    "new_logs", {}, room="logs",
                )
            except Exception as e:
                logger.debug("failed to emit status. Exception: %s", e)


@sio.on("door")
async def door_socket(sid, data):
    await authenticate_socket(sid, "enter")

    if isinstance(data, dict) and isinstance(data.get("open", None), bool):
        interface = sio.get_environ(sid)["aiohttp.request"].app["serial"]
        await interface.open(data.get("open", False))
        return {"Ok": True}


@sio.on("reset")
async def reset(sid):
    await authenticate_socket(sid, "admin")
    interface = sio.get_environ(sid)["aiohttp.request"].app["serial"]
    await interface.reset()


@sio.on("get_card")
async def get_card(sid):
    await asyncio.gather(
        authenticate_socket(sid, "cards"), authenticate_socket(sid, "users_read")
    )
    await sio.get_environ(sid)["aiohttp.request"].app["serial"].card_event.wait()
    try:
        return {"uid": sio.get_environ(sid)["aiohttp.request"].app["serial"].last_uid}
    except KeyError:
        pass


@sio.on("modify_users")
async def modify_users(sid, data):
    await asyncio.gather(
        authenticate_socket(sid, "users_read"), authenticate_socket(sid, "users_manage")
    )
    app = sio.get_environ(sid)["aiohttp.request"].app
    edits = []
    for user in data.get("users", []):
        user.pop("edit", None)
        user["permissions"] = [
            permission
            for permission, value in user.get("permissions", {}).items()
            if value
        ]
        current_username = user.pop("current_username", user.get("username", None))
        edits.append(modify_user(app, current_username=current_username, **user))
    await asyncio.gather(*edits)
    await send_users(sid, broadcast=False)


@sio.on("create_users")
async def create_users(sid, data):
    await asyncio.gather(
        authenticate_socket(sid, "users_read"), authenticate_socket(sid, "users_manage")
    )
    app = sio.get_environ(sid)["aiohttp.request"].app
    if len(data.get("users", [])) > 0:
        for user in data["users"]:
            user["password"] = hasher.hash(user["password"])
        await create_users_in_db(app, data.get("users", []))
    await send_users(sid, broadcast=False)


@sio.on("delete_user")
async def delete_user(sid, data):
    await authenticate_socket(sid, "users_manage")
    app = sio.get_environ(sid)["aiohttp.request"].app
    await delete_user_from_db(app, username=data.get("username", None))
    await send_users(sid, broadcast=False)


@sio.on("settings")
async def settings(sid, data):
    await authenticate_socket(sid, "admin")
    app = sio.get_environ(sid)["aiohttp.request"].app
    if data.get("breaks", False):
        for time in data["breaks"]:
            time["from"] = dt(
                2020, 2, 2, int(time["from"][:2]), int(time["from"][3:]), 0, 0
            )
            time["to"] = dt(2020, 2, 2, int(time["to"][:2]), int(time["to"][3:]), 0, 0)
        data["break_times"] = data.pop("breaks")
    await save_settings(app, data)
    await send_settings(sid, data, broadcast=False)


@sio.on("serial_command")
async def serial_command(sid, data):
    await authenticate_socket(sid, "admin")
    app = sio.get_environ(sid)["aiohttp.request"].app
    command = data.get("command", False)
    if command:
        await app["serial"].writeline(command)


async def send_users(sid, data={}, broadcast=False):
    app = sio.get_environ(sid)["aiohttp.request"].app
    users = await (await get_users(app, ["username", "permissions", "cards"])).to_list(
        None
    )
    logger.debug("socket got a message")
    # ensure all sent users have permissions
    users = await asyncio.gather(*map(lambda user: map_permissions(app, user), users))
    room = "users" if broadcast else sid
    await sio.emit("users", data={"users": users}, room=room)


async def send_settings(sid, data={}, broadcast=False):
    app = sio.get_environ(sid)["aiohttp.request"].app
    settings = await get_settings(app)
    for break_time in settings["breaks"]:
        break_time["from"] = break_time.get("from").strftime("%H:%M")
        break_time["to"] = break_time.get("to").strftime("%H:%M")
    room = "settings" if broadcast else sid
    await sio.emit("settings", data=settings, room=room)


# permissions for rooms
rooms = {
    "door": {"permissions": ["enter"], "function": None},
    "users": {"permissions": ["users_manage", "users_read"], "function": send_users},
    "settings": {"permissions": ["admin"], "function": send_settings},
    "serial_console": {"permissions": ["admin"], "function": None},
}


@sio.on("enter_room")
async def enter_room(sid, data):
    """
    Enter a socketio room specified in `room` property inside socket data
    """
    if not isinstance(data.get("room", False), str) or not rooms.get(
        data["room"], {}
    ).get("permissions", False):
        # TODO use an actual http error here
        return
    # check all room permissions
    await asyncio.gather(
        *[
            authenticate_socket(sid, permission)
            for permission in rooms[data["room"]]["permissions"]
        ]
    )
    sio.enter_room(sid, data["room"])
    if callable(rooms.get(data["room"], {}).get("function", False)):
        await rooms[data["room"]]["function"](sid, data, broadcast=False)


async def map_permissions(app, user):
    if not isinstance(user.get("permissions", False), list):
        user = await set_default_permissions(app, user.get("username", None))
    is_admin = "admin" in user.get("permissions", [])
    user["permissions"] = {
        permission: (is_admin or permission in user.get("permissions", []))
        for permission in permissions_available
    }
    return user
