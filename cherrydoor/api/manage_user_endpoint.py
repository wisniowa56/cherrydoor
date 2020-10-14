import datetime as dt
import json
from typing import List

from aiojobs.aiohttp import atomic
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict, Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions, check_if_self, register_user
from cherrydoor.database import (
    find_user_by_username,
    find_user_by_uid,
    modify_user,
    user_exists,
    delete_user,
)
from cherrydoor.util import get_datetime


class ManageUserEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return [
            "/user",
        ]

    @atomic
    async def post(self, request: Request) -> Response:
        """
        ---
        summary: Update user information
        description:
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - users
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: username of the user you want to modify
                            new_username:
                                type: string
                                description: new name for the user
                            cards:
                                type: array
                                description: list of all cards that will be assigned to the user
                                items:
                                    type: string
                                    format: mifare uid
                                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            card:
                                type: string
                                description: a single card you want to add to the user
                                format: mifare uid
                                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            permissions:
                                type: array
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
                                        - dashboard
                            permission:
                                type: string
                                description: a single permission you want to give the user
                                enum:
                                    - admin
                                    - enter
                                    - logs
                                    - users_read
                                    - users_manage
                                    - cards
                                    - dashboard
                        example:
                            username: notAdministrator
                            new_username: Administrator
                            card: ABABABAB
                            permission: admin
        responses:
            "200":
                description: A JSON document indicating success
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
            "404":
                description: A JSON document indicating error in request (user not found)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'

        """

        data = await request.json()
        username = request.match_info.get("username", False) or data.get(
            "username", False
        )
        if not username:
            raise HTTPBadRequest(
                reason="no username provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no username provided", "status_code": 401}
                ),
                content_type="application/json",
            )

        user = await find_user_by_username(
            request.app, username, ["_id", "permissions"]
        )
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested username exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested username exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        is_self = await check_if_self(request, user.get("_id", None))
        required_permissions = list(data.get("permissions", []))
        if data.get("permission", False):
            required_permissions.append(data["permission"])
        if not is_self:
            required_permissions.append("users_manage")

        await check_api_permissions(request, required_permissions)
        user = modify_user(
            request.app,
            user["_id"],
            username=data.get("new_username", None),
            cards=data.get("cards", None),
            card=data.get("card", None),
            permissions=data.get("permissions", None),
            permission=data.get("permission", None),
        )
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )

    @atomic
    async def patch(self, request: Request) -> Response:
        """
        ---
        summary: Update user information
        description:
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - users
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: username of the user you want to modify
                            new_username:
                                type: string
                                description: new name for the user
                            cards:
                                type: array
                                description: list of all cards that will be assigned to the user
                                items:
                                    type: string
                                    format: mifare uid
                                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            card:
                                type: string
                                description: a single card you want to add to the user
                                format: mifare uid
                                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            permissions:
                                type: array
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
                            permission:
                                type: string
                                description: a single permission you want to give the user
                                enum:
                                    - admin
                                    - enter
                                    - logs
                                    - users_read
                                    - users_manage
                                    - cards
                        example:
                            username: notAdministrator
                            new_username: Administrator
                            card: ABABABAB
                            permission: admin
        responses:
            "200":
                description: A JSON document indicating success
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
            "404":
                description: A JSON document indicating error in request (user not found)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'

        """
        return await self.post(request)

    @atomic
    async def put(self, request: Request) -> Response:
        """
        ---
        summary: Create a new user
        description:
        security:
            - Bearer Authentication: [users_manage]
            - X-API-Key Authentication: [users_manage]
            - Session Authentication: [users_manage]
        tags:
            - users
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
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
                            username: example
                            password: hunter2
                            cards:
                                - ABABABAB
                                - 12345678
                            permissions: enter
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
        permissions = data.get("permissions", [])
        if not isinstance(permissions, list):
            permissions = [permissions]
        await check_api_permissions(request, ["users_manage", *permissions])
        username = data.get("username", False)
        if not username:
            raise HTTPBadRequest(
                reason="no username provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no username provided", "status_code": 401}
                ),
                content_type="application/json",
            )
        user = await user_exists(request.app, username)
        if user:
            raise HTTPConflict(
                reason="User with this username already exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "User with this username already exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        cards = data.get("cards", [])
        if not isinstance(cards, list):
            cards = [cards]
        uid = register_user(
            request.app, username, data.get("password", None), permissions, cards
        )
        user = find_user_by_uid(request.app, uid, ["username", "cards", "permissions"])
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )

    @atomic
    async def delete(self, request: Request) -> Response:
        """
        ---
        summary: Delete a user
        description:
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - users
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: username of the user you want to modify
                                required: true
                        example:
                            username: example
        responses:
            "200":
                description: A JSON document indicating success
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Ok'

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
        username = data.get("username", False)
        if not username:
            raise HTTPBadRequest(
                reason="no username provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no username provided", "status_code": 401}
                ),
                content_type="application/json",
            )
        user = await find_user_by_username(
            request.app, username, ["_id", "permissions"]
        )
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested username exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested username exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        is_self = await check_if_self(request, user.get("_id", None))
        if not is_self:
            await check_api_permissions(request, ["users_manage"])
        await delete_user(request.app, user.get("_id", None), username)
        return respond_with_json({"Ok": True, "Error": None, "status_code": 200})


class ManageUserUrlEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return [
            "/user/{username}",
            "/user/username/{username}",
        ]

    @atomic
    async def post(self, request: Request) -> Response:
        """
        ---
        summary: Update user information
        description:
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - users
        parameters:
            - name: username
              in: path
              description: The name of the user you want to modify (can also be put in request body)
              schema:
                type: string
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: username of the user you want to modify
                            new_username:
                                type: string
                                description: new name for the user
                            cards:
                                type: array
                                description: list of all cards that will be assigned to the user
                                items:
                                    type: string
                                    format: mifare uid
                                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            card:
                                type: string
                                description: a single card you want to add to the user
                                format: mifare uid
                                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            permissions:
                                type: array
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
                                        - dashboard
                            permission:
                                type: string
                                description: a single permission you want to give the user
                                enum:
                                    - admin
                                    - enter
                                    - logs
                                    - users_read
                                    - users_manage
                                    - cards
                                    - dashboard
                        example:
                            username: notAdministrator
                            new_username: Administrator
                            card: ABABABAB
                            permission: admin
        responses:
            "200":
                description: A JSON document indicating success
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
            "404":
                description: A JSON document indicating error in request (user not found)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'

        """

        data = await request.json()
        username = request.match_info.get("username", False) or data.get(
            "username", False
        )
        if not username:
            raise HTTPBadRequest(
                reason="no username provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no username provided", "status_code": 401}
                ),
                content_type="application/json",
            )

        user = await find_user_by_username(
            request.app, username, ["_id", "permissions"]
        )
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested username exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested username exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        is_self = await check_if_self(request, user.get("_id", None))
        required_permissions = list(data.get("permissions", []))
        if data.get("permission", False):
            required_permissions.append(data["permission"])
        if not is_self:
            required_permissions.append("users_manage")

        await check_api_permissions(request, required_permissions)
        user = modify_user(
            request.app,
            user["_id"],
            username=data.get("new_username", None),
            cards=data.get("cards", None),
            card=data.get("card", None),
            permissions=data.get("permissions", None),
            permission=data.get("permission", None),
        )
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )

    @atomic
    async def patch(self, request: Request) -> Response:
        """
        ---
        summary: Update user information
        description:
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - users
        parameters:
            - name: username
              in: path
              description: The name of the user you want to modify (can also be put in request body)
              schema:
                type: string
        requestBody:
            description: JSON containing the changes to the user and/or their username to find them
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: username of the user you want to modify
                            new_username:
                                type: string
                                description: new name for the user
                            cards:
                                type: array
                                description: list of all cards that will be assigned to the user
                                items:
                                    type: string
                                    format: mifare uid
                                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            card:
                                type: string
                                description: a single card you want to add to the user
                                format: mifare uid
                                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                            permissions:
                                type: array
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
                            permission:
                                type: string
                                description: a single permission you want to give the user
                                enum:
                                    - admin
                                    - enter
                                    - logs
                                    - users_read
                                    - users_manage
                                    - cards
                        example:
                            username: notAdministrator
                            new_username: Administrator
                            card: ABABABAB
                            permission: admin
        responses:
            "200":
                description: A JSON document indicating success
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
            "404":
                description: A JSON document indicating error in request (user not found)
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Error'

        """
        return await self.post(request)
