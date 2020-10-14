import datetime as dt
import json
from typing import List

from aiohttp.web import HTTPBadRequest, HTTPNotFound, Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions
from cherrydoor.database import find_user_by
from cherrydoor.util import get_datetime

allowed_search_parameters = ["username", "api_key", "card"]


class FindUserEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return [
            "/user",
            "/user/{username}",
            "/user/username/{username}",
            "/user/card/{card}",
            "/user/key/{api_key}/",
        ]

    async def get(self, request: Request) -> Response:
        """
        ---
        summary: Find user
        description:
        security:
            - Bearer Authentication: [users_read]
            - X-API-Key Authentication: [users_read]
            - Session Authentication: [users_read]
        tags:
            - users
        parameters:
            - name: username
              in: query
              description: A unique username of an user
              schema:
                type: string
            - name: username
              in: path
              description: A unique username of an user
              allowReserved: true
              schema:
                type: string
            - name: card
              in: query
              description: UID of a card connected with the user
              schema:
                type: string
                format: mifare uid
                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
            - name: card
              in: path
              description: UID of a card connected with the user
              schema:
                type: string
                format: mifare uid
                pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
            - name: api_key
              in: query
              description: An API key associated with to the user
              schema:
                type: string
                format: Branca
            - name: api_key
              in: path
              description: An API key associated with to the user
              schema:
                type: string
                format: Branca
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
        await check_api_permissions(request, ["users_read"])
        parameters = {**request.match_info, **request.query}
        search_keys, search_values = zip(
            *(
                {
                    key: parameters[key]
                    for key in allowed_search_parameters
                    if parameters.get(key, None) != None
                }.items()
            )
        )
        user = await find_user_by(
            request.app,
            list(search_keys),
            list(search_values),
            ["username", "cards", "permissions"],
        )
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested data exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested data exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )
