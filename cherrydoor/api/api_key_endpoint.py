from typing import List

import aiohttp_csrf
from aiojobs.aiohttp import atomic
from aiohttp.web import Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions


class DoorEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return ["/api-key", "/api-key/{key}"]

    async def get(self, request: Request) -> Response:
        """
        ---
        summary: Find information about an api key
        description: Decodes and returns token name, username of the user token is associated with, permissions that it has and the token itself
        security:
            - Bearer Authentication: [users_read]
            - X-API-Key Authentication: [users_read]
            - Session Authentication: [users_read]
        tags:
            - API
            - users
        parameters:
            - name: key
              in: query
              description: API token
              schema:
                type: string
                format: Branca
            - name: key
              in: path
              description: API token
              allowReserved: true
              schema:
                type: string
                format: Branca
        responses:
            "200":
                description: A JSON document indicating success
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/APIKeyData'

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
        await check_api_permissions(request, ["users_read"])
        parameters = {**request.match_info, **request.query}
        if not parameters.get("key", False):
            raise HTTPBadRequest(
                reason="no key provided",
                body=json.dumps(
                    {"Ok": False, "Error": "no key provided", "status_code": 401}
                ),
                content_type="application/json",
            )
        key_data, user = await app["api_tokens"].get_token_info()
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested key exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested data exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        token = {
            "name": key_data.get("token_name", None),
            "username": user.get("username", None),
            "permissions": key_data.get("permissions", None),
            "key": parameters.get("key", None),
        }
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "token": token}
        )

    @atomic
    async def post(self, request: Request) -> Response:
        """
        ---
        summary: Generate a new api key
        security:
            - Bearer Authentication: [users_manage, self]
            - X-API-Key Authentication: [users_manage, self]
            - Session Authentication: [users_manage, self]
        tags:
            - API
            - users
        requestBody:
            description: JSON containing instructions to open or close the door.
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            username:
                                type: string
                                description: The name of the user you want to create the token for
                                required: true
                            permissions:
                                type: array
                                description: Permission for the token - "*" means all permissions the user has (you can't give a token permissions that the user doesn't have)
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
                                        - "*"
                                default: ["*"]
                            token_name:
                                type: string
                                description: a friendly name for the token
                                default: uuidv4()
                        example:
                            username: Administrator
                            permissions: ["admin"]
                            token_name: admin token
        responses:
            "200":
                description: A JSON document indicating success
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/APIKeyData'
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
        required_permissions = list(data.get("permissions", []))
        if data.get("permission", False):
            required_permissions.append(data["permission"])
        if not is_self:
            required_permissions.append("users_manage")

        await check_api_permissions(request, required_permissions)

        key, token_name, permissions = app["api_tokens"].generate_token(
            username, data.get("token_name", None), data.get("permissions", ["*"]),
        )
        token = {
            "name": token_name,
            "username": username,
            "permissions": permissions,
            "key": key,
        }
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "token": token}
        )
