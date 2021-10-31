"""Authentication and authorization policies and helpers."""

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
    """aiohttp_security AuthorizationPolicy implementation."""

    def __init__(self, app):
        """Initialize the authorization policy class.

        Parameters
        ----------
        app : aiohttp.web.Application
            The aiohttp application instance.
        """
        self.app = app

    async def authorized_userid(self, identity):
        """Return the username of user from UID.

        Parameters
        ----------
        identity : str
            The user's UID.
        Returns
        -------
        str or None
            The user's username.
        """
        user = await find_user_by_uid(self.app, identity, ["username"])
        if user:
            return user.get("username", None)
        return None

    async def permits(self, identity, permission, context=None):
        """Check if the user has a specific permission.

        Parameters
        ----------
        identity : str
            The user's UID.
        permission : str
            The permission to check.
        context : str, optional
            The context to check (unused).
        Returns
        -------
        bool
            True if the user has the permission or is an admin, False otherwise.
        """
        user = await find_user_by_uid(self.app, identity, ["permissions"])
        if user is None:
            return False
        if "admin" in user.get("permissions", []):
            return True
        return permission in user.get("permissions", [])


class SessionIdentityPolicy(AbstractIdentityPolicy):
    """aiohttp_security Session Identity Policy implementation."""

    def __init__(self, session_key="AIOHTTP_SECURITY", max_age=31536000):
        """Initialize the session identity policy class.

        Parameters
        ----------
        session_key : str, default: "AIOHTTP_SECURITY"
            The key in session to store the identity value at.
        max_age : int, default: 31536000
            The maximum age of the session cookie.
        """
        self._session_key = session_key
        self.max_age = max_age

    async def identify(self, request):
        """Return the identity of the user from session.

        Parameters
        ----------
        request : aiohttp.web.Request
            The request to get the identity from.
        Returns
        -------
        str
            The user's UID.
        """
        session = await get_session(request)
        return session.get(self._session_key)

    async def remember(self, request, response, identity, **kwargs):
        """Save the user identity in the session.

        Parameters
        ----------
        request : aiohttp.web.Request
            The request to get the identity from.
        response : aiohttp.web.Response
            The response to save the identity to.
        identity : str
            The user's UID.
        Other Parameters
        ----------------
        remember : bool, optional
            Whether to remember the identity longer than browser session.
        """
        session = await new_session(request)
        if kwargs.get("remember", False):
            session.max_age = self.max_age
        session[self._session_key] = identity

    async def forget(self, request, response=None):
        """Remove the identity from the session.

        Parameters
        ----------
        request : aiohttp.web.Request
            The request to remove the identity from.
        response : aiohttp.web.Response
            The response to remove the identity from.
        """
        session = await get_session(request)
        session.pop(self._session_key, None)


async def rehash_password(app, identity, password):
    """Rehash the user's password after parameters have been changed.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance.
    identity : str
        The user's UID.
    password : str
        The user's password (in plaintext).
    """
    hashed_password = hasher.hash(password)
    await change_user_password(app, identity, hashed_password)


async def check_credentials(app, username, password=None):
    """Validate the user's credentials.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance.
    username : str
        The user's username.
    password : str, optional
        The user's password (in plaintext).
    Returns
    -------
    tuple(bool, str or None)
        A tuple containing a boolean indicating whether the credentials are valid and if so, user's UID.
    """
    logger.debug("checking credentials for %s", username)
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


async def register_user(app, username, password=None, permissions=None, cards=None):
    """Create a new user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance.
    username : str
        The new user's username.
    password : str, optional
        The new user's password (in plaintext).
    permissions : list, optional
        The list of new user's permissions.
    cards : list, optional
        The list of new user's card UIDs.
    Returns
    -------
    tuple(bool, str or None)
        A tuple containing a boolean indicating whether the user was created and the user's UID or None if the user already existed.
    """
    permissions = permissions if permissions else ["enter"]
    cards = cards if cards else []
    if isinstance(password, str):
        hashed_password = hasher.hash(password)
    else:
        hashed_password = None
    if not await user_exists(app, username):
        uid = await create_user(app, username, hashed_password, permissions, cards)
        return True, uid
    return False, None


async def register_users(app, users):
    """Create multiple users from a list.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance.
    users : list(dict)
        The list of new users with each user having username, password, permissions and cards (optional).
    """
    for user in users:
        if user.get("password", False):
            user["password"] = hasher.hash(user["password"])
    return await create_users(app, users)


async def api_auth(request, permissions=None):
    """Authenticate an API request with an API key or a valid user session.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request to authenticate. Has to contain an Authorization, X-API-Key header or a valid user session cookie.
    permissions : list, optional
        The list of permissions required to access the resource.
    Returns
    -------
    bool
        True if the user has all the permissions required to access the resource.
    """
    permissions = permissions if permissions else []
    bearer = request.headers.get("Authorization", False)
    x_api_key = request.headers.get("X-API-Key", False)
    if bearer:
        token = bearer.replace("Bearer ", "")
        return await request.app["api_tokens"].validate_token(
            token, permissions, raise_error=True
        )
    if x_api_key:
        return await request.app["api_tokens"].validate_token(
            x_api_key, permissions, raise_error=True
        )
    return all(
        await asyncio.gather(
            *[check_permission(request, permission) for permission in permissions]
        )
    )


async def check_api_permissions(request, permissions):
    """Check if the API request is authorized to have specific permissions.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request to check permissions for.
    permissions : list
        The list of permissions to check.
    Returns
    -------
    bool
        True if the user has all the permissions required to access the resource.
    Raises
    ------
    aiohttp.web.HTTPForbidden
        If the user does not have all the permissions required to access the resource.
    aiohttp.web.HTTPUnauthorized
        If the request does not contain an API key and no user is logged in for session.
    """
    try:
        return bool(await api_auth(request, list(permissions)))
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
    """Check if the user making an action against their own account.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request to check permissions for.
    uid : str
        The user ID of the user who the action is being made against.
    Returns
    -------
    bool
        True if the user making the action is the same as the user being accessed.
    """
    bearer = request.headers.get("Authorization", False)
    x_api_key = request.headers.get("X-API-Key", False)
    if bearer:
        request_user = find_user_by_token(request.app, bearer, ["_id"])
    elif x_api_key:
        request_user = find_user_by_token(request.app, x_api_key, ["_id"])
    else:
        request_uid = await authorized_userid(request)
        return request_uid == uid
    return request_user is not None and request_user.get("_id", "") == uid


async def get_permissions(request):
    """Get the list of permissions for a user.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request to get permissions for.
    Returns
    -------
    list
        The list of permissions for the user.
    """
    username = await authorized_userid(request)
    permission_list = await list_permissions(request.app, username)
    is_admin = "admin" in permission_list
    user_permissions = {
        permission: (is_admin or permission in permission_list)
        for permission in permissions_available
    }
    return user_permissions
