"""
Create and validate Branca-based API tokens
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import logging
from hashlib import sha3_256
from uuid import uuid4

import msgpack
from aiohttp.web import HTTPForbidden, HTTPUnauthorized
from aiohttp_security import check_permission
from branca import Branca

from cherrydoor.database import (
    add_token_to_user,
    find_user_by_token,
    find_user_by_username,
)

logger = logging.getLogger("API_TOKENS")


class ApiTokens:
    def __init__(self, app, secret):
        self.app = app
        self.branca = Branca(key=sha3_256(secret.encode("utf-8")).digest())
        logger.debug("created Branca instance")

    async def generate_token(self, username, token_name=str(uuid4()), permissions="*"):
        if not token_name:
            token_name = str(uuid4())
        logger.debug(
            f"generating a token for {username} with these permissions: {permissions}"
        )
        user = await find_user_by_username(
            self.app, username, ["permissions", "password", "_id"]
        )
        if permissions == "*":
            permissions = list(user.get("permissions", []))
        else:
            permissions = list(
                filter(
                    lambda permission: permission in user.get("permissions", []),
                    permissions,
                )
            )
        packed = msgpack.dumps(
            {"username": username, "permisisons": permissions, "token_name": token_name}
        )
        token = self.branca.encode(packed)
        logger.debug(
            f"successfuly generated a token for {username}: {token}. Adding it to the database"
        )
        await add_token_to_user(self.app, user.get("_id", ""), token_name, token)
        return (
            token,
            token_name,
            permissions,
        )

    async def validate_token(self, token, permissions=[], raise_error=False):
        logger.debug(
            f"validating a token{' for permissions' + permissions if permissions != [] else ''}. Token: {token}"
        )
        user = await find_user_by_token(self.app, token, ["permissions", "username"])
        packed = self.branca.decode(token)
        payload = msgpack.loads(packed, raw=False)
        logger.debug(f"decoded token: {payload}")
        if user == None:
            if raise_error:
                raise HTTPUnauthorized()
            return False
        user_permission_set = set(user.get("permissions", []))
        if not set(payload.get("permissions", [])).issubset(user_permission_set):
            payload["permissions"] = filter(
                lambda permission: permission in user_permission_set,
                payload["permissions"],
            )
        if (
            # check if token has all requested permissions
            not set(permissions).issubset(set(payload.get("permissions", [])))
            # check if user has all requested permissions
            or not set(permissions).issubset(user_permission_set)
        ):
            if raise_error:
                raise HTTPForbidden()
            return False
        logger.debug("Token is valid")
        return True

    async def get_token_info(self, token):
        user = await find_user_by_token(self.app, token, ["permissions", "username"])
        packed = self.branca.decode(token)
        payload = msgpack.loads(packed, raw=False)
        if user == None:
            return payload, None
        user_permission_set = set(user.get("permissions", []))
        if not set(payload.get("permissions", [])).issubset(user_permission_set):
            payload["permissions"] = filter(
                lambda permission: permission in user_permission_set,
                payload["permissions"],
            )
        return payload, user
