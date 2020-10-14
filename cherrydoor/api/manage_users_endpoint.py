import datetime as dt
import json
from typing import List

from aiojobs.aiohttp import atomic
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict, Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions, check_if_self, register_users
from cherrydoor.database import (
    find_user_by_username,
    find_user_by_uid,
    modify_user,
    user_exists,
    create_user,
    delete_user,
)
from cherrydoor.util import get_datetime


class ManageUsersEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return ["/users"]

    @atomic
    async def put(self, request: Request) -> Response:
        """
        ---
        summary: Create multiple new users
        description:
        security:
            - Bearer Authentication: [users_manage]
            - X-API-Key Authentication: [users_manage]
            - Session Authentication: [users_manage]
        tags:
            - users
        requestBody:
            description: JSON containing a list of new user objects
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            users:
                                type: array
                                items:
                                    type: object
                                    properties:
                                        username:
                                            type: string
                                            description: username of the user you want to modify
                                            required: true
                                        password:
                                            type: string
                                            description: unhashed password that will be hashed before being added to the user
                                        cards:
                                            description: a single card or list of cards that will be assigned to the user
                                            oneOf:
                                                - type: array
                                                  description: list of all cards that will be assigned to the user
                                                  items:
                                                    type: string
                                                    format: mifare uid
                                                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                                                - type: string
                                                  description: a single card that will be assigned to the user
                                                  format: mifare uid
                                                  pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                                        permissions:
                                            description: a single permission or list of permissions that the user will have (you need to have a permission to assign it to others)
                                            oneOf:
                                                - type: array
                                                  description: list of all permissions that the user will have
                                                  items:
                                                    type: string
                                                    enum:
                                                        - admin
                                                        - enter
                                                        - logs
                                                        - users_read
                                                        - users_manage
                                                        - cards
                                                - type: string
                                                  description: a single permission you want to give the user
                                                  enum:
                                                    - admin
                                                    - enter
                                                    - logs
                                                    - users_read
                                                    - users_manage
                                                    - cards
                        example:
                            users:
                                - username: example
                                  password: hunter2
                                  cards:
                                    - ABABABAB
                                    - 12345678
                                  permissions: enter
                                - username: example2
                                  password: hunter4
                                  cards: FFFFFFFF
                                  permissions:
                                    - enter
                                    - cards
                                    - users_read
        responses:
            "200":
                description: A JSON document indicating success along with some information about the user
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/User'

            "401":
                description: A JSON document indicating error in request (user not authenticated)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'
            "403":
                description: A JSON document indicating error in request (user doesn't have permission to preform this action)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'
            "409":
                description: A JSON document indicating error in request (user already exists)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'
        """

        data = await request.json()
        if isinstance(data.get("users", None), list):
            users = data["users"]
        elif isinstance(data.get("users", ""), str):
            users = [data.get("users", "")]
        else:
            raise HTTPBadRequest(
                reason="no users provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no users provided", "status_code": 401}
                ),
                content_type="application/json",
            )
        permissions = set()
        for user in users:
            user_permissions = user.get("permissions", [])
            if not isinstance(user_permissions, list):
                user_permission = [user_permissions]
            permissions.update(set(user_permissions))
        await check_api_permissions(request, ["users_manage", *permissions])
        result_users = []
        for user_data in users:
            username = user_data.get("username", False)
            if not username:
                raise HTTPBadRequest(
                    reason="no username provided for at least one user",
                    body=json.dumps(
                        {
                            "Ok": False,
                            "Error": "no username provided for at least one user",
                            "status_code": 401,
                        }
                    ),
                    content_type="application/json",
                )
            user = await user_exists(request.app, username)
            if user:
                raise HTTPConflict(
                    reason=f"User with this username ({username}) already exists",
                    body=json.dumps(
                        {
                            "Ok": False,
                            "Error": f"User with this username ({username}) already exists",
                            "status_code": 409,
                        }
                    ),
                    content_type="application/json",
                )
            cards = user_data.get("cards", [])
            if not isinstance(cards, list):
                user_data["cards"] = [cards]
        await register_users(request.app, users)
        users = [
            {
                "username": user.get("username"),
                "cards": user.get("cards", []),
                "permissions": user.get("permissions", []),
            }
            for user in users
        ]
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "users": users}
        )
