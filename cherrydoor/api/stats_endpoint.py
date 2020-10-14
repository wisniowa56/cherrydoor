import datetime as dt
import json
from typing import List

from aiohttp.web import HTTPBadRequest, Request
from aiohttp.web_response import Response
from aiohttp_rest_api import AioHTTPRestEndpoint
from aiohttp_rest_api.responses import respond_with_json

from cherrydoor.auth import check_api_permissions
from cherrydoor.database import get_grouped_logs
from cherrydoor.util import get_datetime


class StatsEndpoint(AioHTTPRestEndpoint):
    def connected_routes(self) -> List[str]:
        """"""
        return ["/stats"]

    async def get(self, request: Request) -> Response:
        """
        ---
        summary: Usage statistics
        description: Get usage statistics between specified dates - defaults to last week - and with specified granularity - defaults to a day
        security:
            - Bearer Authentication: [logs]
            - X-API-Key Authentication: [logs]
            - Session Authentication: [logs]
        tags:
            - logs
        parameters:
            - name: start
              in: query
              required: false
              description: ISO Date or timestamp that will be the starting point (inclusive) of returned stats
              schema:
                oneOf:
                    - type: string
                      format: date-time
                    - type: integer
                      format: timestamp
            - name: end
              in: query
              required: false
              description: ISO Date or timestamp that will be the ending point (inclusive) of returned stats
              schema:
                oneOf:
                    - type: string
                      format: date-time
                    - type: integer
                      format: timestamp
            - name: granularity
              in: query
              required: false
              description: interval of time for each data point returned
              schema:
                type: integer
                default: 86400
        responses:
            "200":
                description: A JSON document indicating success
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Stats'

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
        await check_api_permissions(request, ["logs"])
        try:
            datetime_from, datetime_to, granularity = (
                get_datetime(
                    request.query.get("start", ""),
                    dt.datetime.now() - dt.timedelta(days=7),
                ),
                get_datetime(request.query.get("end", ""), dt.datetime.now()),
                dt.timedelta(seconds=int(request.query.get("granularity", 86400))),
            )
        except ValueError as e:
            raise HTTPBadRequest(
                reason=str(e),
                body=json.dumps({"Ok": False, "Error": str(e), "status_code": 401}),
                content_type="application/json",
            )
        stats = await get_grouped_logs(
            request.app, datetime_from, datetime_to, granularity
        )
        return respond_with_json(
            {"Ok": True, "Error": None, "status_code": 200, "stats": stats}
        )
