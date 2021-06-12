import datetime as dt
import json
from typing import List

from aiojobs.aiohttp import atomic
from aiohttp.web import HTTPBadRequest, HTTPNotFound, Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions
from cherrydoor.database import (
    find_user_by,
    find_user_by_cards,
    add_cards_to_user,
    delete_cards_from_user,
)
from cherrydoor.util import get_datetime

allowed_search_parameters = ["username", "api_key", "card"]


class FindUserEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return [
            "/card",
            "/card/{uid}",
        ]

    async def get(self, request: Request) -> Response:
        """
        ---
        summary: Find a user with the card/s
        description:
        security:
            - Bearer Authentication: [users_read]
            - X-API-Key Authentication: [users_read]
            - Session Authentication: [users_read]
        tags:
            - cards
        parameters:
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
            - name: cards
              in: query
              description: Array of card UIDs connected with the user (will search for user with **all** cards)
              schema:
                type: array
                items:
                    type: string
                    format: mifare uid
                    pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
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
        if parameters.get("card", False):
            cards = [parameters["card"]]
        else:
            cards = list(parameters.get("cards", []))
        user = await find_user_by_cards(
            request.app, cards, ["username", "cards", "permissions"],
        )
        if user == None:
            raise HTTPNotFound(
                reason="no user with requested cards exists",
                body=json.dumps(
                    {
                        "Ok": False,
                        "Error": "no user with requested cards exists",
                        "status_code": 404,
                    }
                ),
                content_type="application/json",
            )
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )

    @atomic
    async def put(self, request: Request) -> Response:
        """
        ---
        summary: Add card/s to user
        description:
        security:
            - Bearer Authentication: [cards, self]
            - X-API-Key Authentication: [cards, self]
            - Session Authentication: [cards, self]
        tags:
            - cards
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
                            cards:
                                required: true
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
                        example:
                            username: example
                            cards:
                                - ABABABAB
                                - 12345678
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
                description: A JSON document indicating error in request (card already exists on user)
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
        user = await find_user_by_username(request.app, username, ["_id", "cards"])
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
            await check_api_permissions(request, ["cards"])
        cards = data.get("cards", [])
        if not isinstance(cards, list):
            cards = [cards]
        user = await add_cards_to_user(request.app, user["_id"], cards)
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )

    @atomic
    async def delete(self, request: Request) -> Response:
        """
        ---
        summary: Delete card/s from user
        description:
        security:
            - Bearer Authentication: [cards, self]
            - X-API-Key Authentication: [cards, self]
            - Session Authentication: [cards, self]
        tags:
            - cards
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
                            cards:
                                required: true
                                oneOf:
                                    - type: array
                                      description: list of all cards that will be removed from the user
                                      items:
                                        type: string
                                        format: mifare uid
                                        pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                                    - type: string
                                      description: a single card that will be removed from the user
                                      format: mifare uid
                                      pattern: '^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$'
                        example:
                            username: example
                            cards:
                                - ABABABAB
                                - 12345678
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
                description: A JSON document indicating error in request (card already exists on user)
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
        user = await find_user_by_username(request.app, username, ["_id", "cards"])
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
            await check_api_permissions(request, ["cards"])
        cards = data.get("cards", [])
        if not isinstance(cards, list):
            cards = [cards]
        user = await delete_cards_from_user(request.app, user["_id"], cards)
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "user": user}
        )
