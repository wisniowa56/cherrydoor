from aiohttp.web import HTTPFound, get

openapi_description = """
# Overview

The following document outlines all API routes available currently in Cherrydoor

"""
openapi_contact = {
    "name": "Samorząd",
    "email": "kontakt@wisniowasu.pl",
    "url": "https://wisniowasu.pl/",
}
openapi_overrides = {
    "openapi": "3.0.2",
    "info": {
        "x-logo": {
            "url": "/static/images/logo/logo-256px.png",
            "description": openapi_description,
        },
        "contact": openapi_contact,
    },
    "tags": [
        {
            "name": "door",
            "description": "Endpoints used to control or check door behavior directly",
        },
        {
            "name": "logs",
            "description": "Endpoints used to retrieve some data from logs",
        },
        {
            "name": "users",
            "description": "Endpoints used to get and create or modify user data",
        },
        {
            "name": "cards",
            "description": "Endpoints used to check cards and delete or modify them",
        },
        {
            "name": "API",
            "description": "Endpoints related to the API itself - for example API keys",
        },
    ],
    "components": {
        "schemas": {
            "Ok": {
                "type": "object",
                "properties": {
                    "Ok": {"type": "boolean", "default": True},
                    "Error": {"nullable": True, "type": "string", "default": None},
                    "status_code": {"type": "integer", "minimum": 200, "maximum": 307},
                },
                "example": {"Ok": True, "Error": None, "status_code": 200},
                "readOnly": True,
            },
            "Error": {
                "type": "object",
                "properties": {
                    "Ok": {"type": "boolean", "default": False},
                    "Error": {"type": "string", "format": "error"},
                    "status_code": {"type": "integer", "minimum": 400, "maximum": 505},
                },
                "example": {
                    "Ok": False,
                    "Error": "Some error occured",
                    "status_code": 400,
                },
                "readOnly": True,
            },
            "Stats": {
                "type": "object",
                "properties": {
                    "Ok": {"type": "boolean", "default": True},
                    "Error": {"nullable": True, "type": "string", "default": None},
                    "status_code": {"type": "integer", "minimum": 200, "maximum": 307},
                    "stats": {
                        "type": "array",
                        "description": "grouped statistics",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date_from": {
                                    "type": "string",
                                    "format": "date-time",
                                    "description": "ISO format date that's the start point of the group",
                                },
                                "date_to": {
                                    "type": "string",
                                    "format": "date-time",
                                    "description": "ISO format date that's the end point of the group",
                                },
                                "count": {
                                    "type": "integer",
                                    "description": "Total amount of authentication attempts",
                                },
                                "successful": {
                                    "type": "integer",
                                    "description": "Amount of successful authentication attempts",
                                },
                                "during_break": {
                                    "type": "integer",
                                    "description": "Amount of authentication attempts that used manufacturer code (happened during a break)",
                                },
                            },
                        },
                    },
                },
                "readOnly": True,
                "example": {
                    "Ok": True,
                    "Error": None,
                    "status_code": 200,
                    "stats": [
                        {
                            "date_from": "2020-01-01T00:00:00.000000",
                            "date_to": "2020-01-02T00:00:00.000000",
                            "count": 100,
                            "successful": 50,
                            "during_break": 25,
                        },
                        {
                            "date_from": "2020-01-03T00:00:00.000000",
                            "date_to": "2020-01-04T00:00:00.000000",
                            "count": 500,
                            "successful": 300,
                            "during_break": 400,
                        },
                    ],
                },
            },
            "User": {
                "type": "object",
                "properties": {
                    "Ok": {"type": "boolean", "default": True},
                    "Error": {"nullable": True, "type": "string", "default": None},
                    "status_code": {"type": "integer", "minimum": 200, "maximum": 307},
                    "user": {
                        "type": "object",
                        "properties": {
                            "username": {
                                "type": "string",
                                "description": "The unique username of an user",
                            },
                            "cards": {
                                "type": "array",
                                "description": "list of all cards associated with the user",
                                "items": {
                                    "type": "string",
                                    "format": "mifare uid",
                                    "pattern": "^([0-9a-fA-F]{8}|([0-9a-fA-F]{14}|[0-9a-fA-F]{20})$",
                                },
                            },
                            "permissions": {
                                "type": "array",
                                "description": "list of all permissions the user has",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "admin",
                                        "enter",
                                        "logs",
                                        "users_read",
                                        "users_manage",
                                        "cards",
                                        "dashboard",
                                    ],
                                },
                            },
                        },
                    },
                },
                "readOnly": True,
                "example": {
                    "Ok": True,
                    "Error": None,
                    "status_code": 200,
                    "user": {
                        "username": "Administrator",
                        "cards": ["AAAAAAAA", "01234567"],
                        "permissions": ["admin"],
                    },
                },
            },
            "APIKeyData": {
                "type": "object",
                "properties": {
                    "Ok": {"type": "boolean", "default": True},
                    "Error": {"nullable": True, "type": "string", "default": None},
                    "status_code": {"type": "integer", "minimum": 200, "maximum": 307},
                    "token": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "name assigned to the token",
                            },
                            "username": {
                                "type": "string",
                                "description": "name of the user the token is assigned to",
                            },
                            "permissions": {
                                "type": "array",
                                "description": "list of all permissions the key allows",
                                "items": {
                                    "type": "string",
                                    "enum": [
                                        "admin",
                                        "enter",
                                        "logs",
                                        "users_read",
                                        "users_manage",
                                        "cards",
                                        "dashboard",
                                    ],
                                },
                            },
                            "key": {
                                "type": "string",
                                "description": "the token itself",
                                "format": "Branca",
                            },
                        },
                    },
                },
                "readOnly": True,
                "example": {
                    "Ok": True,
                    "Error": None,
                    "status_code": 200,
                    "token": {
                        "name": "admin token",
                        "username": "Administrator",
                        "permissions": ["admin"],
                    },
                },
            },
        },
        "securitySchemes": {
            "Bearer Authentication": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "Branca",
                "description": "Use an `Authorization: Bearer <key>` header with an API key with required privileges.\nTakes precedence over all other authentication options",
            },
            "X-API-Key Authentication": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "Use an `X-API-Key: <key>` header with an API key with required privileges.\nSecond checked authentication option",
            },
            "Session Authentication": {
                "type": "apiKey",
                "in": "cookie",
                "name": "session_id",
                "description": "Use a valid user `session_id` cookie to just utilize their privileges.\nOnly checked if no other authentication method was used",
            },
        },
    },
}


async def api_redirect_route(request):
    raise HTTPFound(request.app["redoc_url"])


redoc_options = {}

redoc_routes = [
    get("/api", api_redirect_route),
    get("/api/", api_redirect_route),
    get("/api/docs", api_redirect_route),
    get("/api/docs/", api_redirect_route),
    get("/api/v1", api_redirect_route),
    get("/api/v1/", api_redirect_route),
]
