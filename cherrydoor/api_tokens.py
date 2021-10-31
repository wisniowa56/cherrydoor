"""Create and validate Branca-based API tokens."""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import logging
from hashlib import sha3_256
from uuid import uuid4

import msgpack
from aiohttp.web import HTTPForbidden, HTTPUnauthorized
from branca import Branca

from cherrydoor.database import (
    add_token_to_user,
    find_user_by_token,
    find_user_by_username,
)

logger = logging.getLogger("API_TOKENS")


class ApiTokens:
    """A class for managing branca-based API tokens."""

    def __init__(self, app, secret):
        """Initialize the Api Token manager.

        Parameters
        ----------
        app : aiohttp.web.Application
            The aiohttp application instance
        secret : str
            The secret key used to sign the API tokens (after hashing)
        """
        self.app = app
        self.branca = Branca(key=sha3_256(secret.encode("utf-8")).digest())
        logger.debug("created Branca instance")

    async def generate_token(self, username, token_name=str(uuid4()), permissions="*"):
        """Generate a token for a user with given permissions.

        Parameters
        ----------
        username : str
            The username of the user for whom the token is being generated
        token_name : str, default=str(uuid4())
            The name of the token to be generated - will represent it on the frontend
        permissions : str, default="*"
            The permissions that the token will have acces to. "*" means all permissions user has
        Returns
        -------
        (token, token_name, permissions) : tuple(str, str, list(str))
            The generated token, its name and permissions it has access to
        """
        if not token_name:
            token_name = str(uuid4())
        logger.debug(
            "generating a token for %s with these permissions: %s",
            username,
            permissions,
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
            "successfuly generated a token for %s: %s. Adding it to the database",
            username,
            token,
        )
        await add_token_to_user(self.app, user.get("_id", ""), token_name, token)
        return (
            token,
            token_name,
            permissions,
        )

    async def validate_token(self, token, permissions=None, raise_error=False):
        """Validate if token is valid and has the requested permissions.

        Parameters
        ----------
        token : str
            The token to be validated
        permissions : list(str), default=None
            The permissions that the token must have access to.
        raise_error : bool, default=False
            If True, raise an error if the token is invalid, otherwise just return False
        Returns
        -------
        bool
            True if the token is valid and has the requested permissions, False otherwise
        """
        permissions = permissions if permissions else []
        logger.debug(
            "validating a token%s. Token: %s",
            " for permissions" + permissions if permissions != [] else "",
            token,
        )
        user = await find_user_by_token(self.app, token, ["permissions", "username"])
        packed = self.branca.decode(token)
        payload = msgpack.loads(packed, raw=False)
        logger.debug("decoded token: %s", payload)
        if user is None:
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
        """Get information about a given token. Includes permissions, username, token name, etc.

        Parameters
        ----------
        token : str
            The token to be checked
        Returns
        -------
        (payload, user) : tuple(dict, dict)
            A dictionary containing information about the token and a dict with user information
            (username, user permissions)

        """
        user = await find_user_by_token(self.app, token, ["permissions", "username"])
        packed = self.branca.decode(token)
        payload = msgpack.loads(packed, raw=False)
        if user is None:
            return payload, None
        user_permission_set = set(user.get("permissions", []))
        if not set(payload.get("permissions", [])).issubset(user_permission_set):
            payload["permissions"] = filter(
                lambda permission: permission in user_permission_set,
                payload["permissions"],
            )
        return payload, user
