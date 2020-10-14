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
        return ["/door"]

    @atomic
    async def post(self, request: Request) -> Response:
        """
        ---
        summary: Open or close the door
        security:
            - Bearer Authentication: [enter]
            - X-API-Key Authentication: [enter]
            - Session Authentication: [enter]
        tags:
            - door
        requestBody:
            description: JSON containing instructions to open or close the door.
            required: true
            content:
                application/json:
                    schema:
                        type: object
                        required:
                            - door
                        properties:
                            door:
                                type: boolean
                        example:
                            door: true
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

        """
        await check_api_permissions(request, ["enter"])
        data = await request.json()
        await request.app["serial"].writeline(f"AUTH {int(data.get('door', 0))}")
        return respond_with_json({"Ok": True, "Error": None, "status_code": 200})
