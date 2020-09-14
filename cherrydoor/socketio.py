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

logger = logging.getLogger("SOCKET.IO")

sio = socketio.AsyncServer(async_mode="aiohttp")


class StatsNamespace(socketio.Namespace):
    async def on_connect(self, sid, environ):
        await authenticate_socket(sid, environ, "logs")
        sio.enter_room(sid, "stats")


async def authenticate_socket(sid, environ, permission):
    with sio.Session(sid) as session:
        if not isinstance(session.get("permissions"), list):
            session["permissions"] = []
        if permission not in session.get("permissions", []):
            try:
                await check_permission(environ, permission)
                session["permissions"].append(permission)
                return True
            except (web.HTTPUnauthorized, web.HTTPForbidden):
                raise socketio.exceptions.ConnectionRefusedError(
                    f"unauthorized - {permission} permission required"
                )
        else:
            return True
