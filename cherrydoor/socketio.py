"""
Websocket handlers
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.7"
__status__ = "Prototype"

import asyncio
import logging

import socketio
from aiohttp_security import check_permission

from aiohttp import web, WSMsgType

from cherrydoor.auth import get_permissions

logger = logging.getLogger("SOCKET.IO")

sio = socketio.AsyncServer(async_mode="aiohttp")


async def authenticate_socket(sid, request, permission):
    with sio.Session(sid) as session:
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


class StatsNamespace(socketio.Namespace):
    async def on_connect(self, sid):
        request = sio.environ[sid]["aiohttp.request"]
        await authenticate_socket(sid, request, "logs")
        sio.enter_room(sid, "stats")


@sio.on("door")
async def door_socket(sid, data):
    request = sio.environ[sid]["aiohttp.request"]
    if isinstance(data, dict) and isinstance(data.get("open", None), bool):
        await request.app["serial"].writeline(
            f"AUTH {1 if data.get('open', False) else 0}"
        )
        return {"Ok": True}
