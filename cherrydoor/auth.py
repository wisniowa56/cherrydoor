"""
Set up authentication and authorization
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"
import asyncio
import logging
from json import dumps

from aiohttp.web import HTTPForbidden, HTTPUnauthorized
from aiohttp_session import get_session, new_session
from aiohttp_security import check_permission, authorized_userid
from aiohttp_security.abc import AbstractAuthorizationPolicy, AbstractIdentityPolicy
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from cherrydoor.database import (
    change_user_password,
    create_user,
    create_users,
    find_user_by_uid,
    find_user_by_username,
    find_user_by_token,
    user_exists,
    list_permissions,
)

logger = logging.getLogger("AUTH")

hasher = PasswordHasher(
    time_cost=4,
    memory_cost=65536,
    parallelism=8,
    hash_len=16,
    salt_len=16,
    encoding="utf-8",
)

permissions_available = [
    "admin",
    "enter",
    "logs",
    "users_read",
    "users_manage",
    "cards",
    "dashboard",
]


class AuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, app):
        self.app = app

    async def authorized_userid(self, identity):
        user = await find_user_by_uid(self.app, identity, ["username"])
        if user:
            return user.get("username", None)
        else:
            return None

    async def permits(self, identity, permission, context=None):
        user = await find_user_by_uid(self.app, identity, ["permissions"])
        if user == None:
            return False
        if "admin" in user.get("permissions", []):
            return True
        else:
            return permission in user.get("permissions", [])


class SessionIdentityPolicy(AbstractIdentityPolicy):
    def __init__(self, session_key="AIOHTTP_SECURITY", max_age=31536000):
        self._session_key = session_key
        self.max_age = max_age

    async def identify(self, request):
        session = await get_session(request)
        return session.get(self._session_key)

    async def remember(self, request, response, identity, **kwargs):
        session = await new_session(request)
        if kwargs.get("remember", False):
            session.max_age = self.max_age
        session[self._session_key] = identity

    async def forget(self, request, response=None):
        session = await get_session(request)
        session.pop(self._session_key, None)


async def rehash_password(app, identity, password):
    hashed_password = hasher.hash(password)
    await change_user_password(app, identity, hashed_password)


async def check_credentials(app, username, password=None):
    logger.debug(f"checking credentials for {username}")
    if isinstance(password, str):
        user = await find_user_by_username(app, username, ["password", "_id"])
        try:
            validate = hasher.verify(
                user.get("password", None).encode("utf-8"), password.encode("utf-8")
            )
            if user.get("password", "") != "" and validate:
                if hasher.check_needs_rehash(user.get("password", "")):
                    asyncio.create_task(
                        rehash_password(app, user.get("_id", ""), password)
                    )
                return True, str(user.get("_id", None))
        except (
            VerificationError,
            AttributeError,
        ):
            pass
    return False, None


async def register_user(app, username, password=None, permissions=["enter"], cards=[]):
    if isinstance(password, str):
        hashed_password = hasher.hash(password)
    else:
        hashed_password = None
    if await user_exists(app, username):
        uid = await create_user(app, username, password, permissions, cards)
        return True, uid
    return False, None


async def register_users(app, users):
    for user in users:
        if user.get("password", False):
            user["password"] = hasher.hash(user["password"])
    await create_users(app, users)


async def api_auth(request, permissions=[]):
    bearer = request.headers.get("Authorization", False)
    x_api_key = request.headers.get("X-API-Key", False)
    if bearer:
        token = bearer.replace("Bearer ", "")
        return await request.app["api_tokens"].validate_token(
            token, permissions, raise_error=True
        )
    elif x_api_key:
        return await request.app["api_tokens"].validate_token(
            x_api_key, permissions, raise_error=True
        )
    else:
        return all(
            await asyncio.gather(
                *[check_permission(request, permission) for permission in permissions]
            )
        )


async def check_api_permissions(request, permissions):
    try:
        if await api_auth(request, list(permissions)):
            return True
        else:
            return False
    except HTTPUnauthorized:
        reason = "No user with this api key/session found"
        raise HTTPUnauthorized(
            reason=reason,
            body=dumps({"Ok": False, "Error": reason, "status_code": 401}),
            content_type="application/json",
        )
    except HTTPForbidden:
        reason = f"Insufficient permissions. Permissions required: {list(permissions)}"
        raise HTTPForbidden(
            reason=reason,
            body=dumps({"Ok": False, "Error": reason, "status_code": 403}),
            content_type="application/json",
        )


async def check_if_self(request, uid):
    bearer = request.headers.get("Authorization", False)
    x_api_key = request.headers.get("X-API-Key", False)
    if bearer:
        request_user = find_user_by_token(request.app, bearer, ["_id"])
    elif x_api_key:
        request_user = find_user_by_token(request.app, x_api_key, ["_id"])
    else:
        request_uid = await authorized_userid(request)
        return request_uid == uid
    return request_user != None and request_user.get("_id", "") == uid


async def get_permissions(request):
    username = await authorized_userid(request)
    permission_list = await list_permissions(request.app, username)
    is_admin = "admin" in permission_list
    user_permissions = {
        permission: (is_admin or permission in permission_list)
        for permission in permissions_available
    }
    return user_permissions
