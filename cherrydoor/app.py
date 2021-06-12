"""
Everything connected to setup of the app
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import asyncio
import base64
import os
from hashlib import sha256
from typing import Any, Dict

import aiohttp_csrf
import sentry_sdk
from aiohttp import web
from aiohttp_jinja2 import get_env
from aiohttp_jinja2 import setup as setup_jinja2
from aiohttp_rest_api.loader import (
    get_openapi_documentation,
    load_and_connect_all_endpoints_from_folder,
)
from aiohttp_rest_api.redoc import setup_redoc
from aiohttp_security import setup as setup_security
from aiohttp_session import setup as setup_session
from aiohttp_session_mongo import MongoStorage
from jinja2 import PackageLoader, contextfunction
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

from cherrydoor.__version__ import __version__
from cherrydoor.api import (
    openapi_contact,
    openapi_description,
    openapi_overrides,
    redoc_options,
    redoc_routes,
)
from cherrydoor.api_tokens import ApiTokens
from cherrydoor.auth import AuthorizationPolicy, SessionIdentityPolicy
from cherrydoor.config import load_config
from cherrydoor.database import init_db, setup_db
from cherrydoor.secure import set_secure_headers
from cherrydoor.secure import setup as secure_setup
from cherrydoor.views import routes as views
from cherrydoor.socketio import sio, setup_socket_tasks

CSRF_FIELD_NAME = "_csrf_token"
CSRF_SESSION_NAME = "csrf_token"
CSRF_HEADER_NAME = "csrf_token"


def setup_app(loop=asyncio.get_event_loop(), config=load_config()[0]):
    if config.get("sentry_dsn", None):
        sentry_sdk.init(
            dsn=config["sentry_dsn"],
            integrations=[AioHttpIntegration()],
            release=f"cherrydoor@{__version__}",
        )
    # create app
    app = web.Application(loop=loop)
    # make config accessible through the app
    app["config"] = config
    # setup database and add it to the app
    db = init_db(config, loop)
    app["db"] = db
    # create a token generator/validator and add make it accessible through the app
    api_tokens = ApiTokens(app, config.get("secret_key", ""))
    app["api_tokens"] = api_tokens

    app.on_startup.append(setup_db)
    # set up aiohttp-session with aiohttp-session-mongo for storage
    setup_session(
        app, MongoStorage(db["sessions"], max_age=None, cookie_name="session_id",),
    )
    # set up aiohttp-security
    setup_security(
        app,
        SessionIdentityPolicy("uid", config.get("max_session_age", 31536000)),
        AuthorizationPolicy(app),
    )
    # set up secure.py
    secure_setup(app)
    app.middlewares.append(set_secure_headers)

    csrf_policy = aiohttp_csrf.policy.FormAndHeaderPolicy(
        CSRF_HEADER_NAME, CSRF_FIELD_NAME
    )
    csrf_storage = aiohttp_csrf.storage.SessionStorage(CSRF_SESSION_NAME)
    aiohttp_csrf.setup(app, policy=csrf_policy, storage=csrf_storage)
    # app.middlewares.append(aiohttp_csrf.csrf_middleware)

    load_and_connect_all_endpoints_from_folder(
        path=f"{os.path.dirname(os.path.realpath(__file__))}/api",
        app=app,
        version_prefix="api/v1",
    )
    redoc_url = "/api/v1/docs"
    setup_redoc(
        app,
        redoc_url=redoc_url,
        description=openapi_description,
        title="Cherrydoor API",
        page_title="Cherrydocs",
        openapi_info=get_openapi_documentation(overrides=openapi_overrides),
        redoc_options=redoc_options,
        contact=openapi_contact,
    )
    app["redoc_url"] = redoc_url
    app.router.add_routes(redoc_routes)
    setup_static_routes(app)

    jinja2_loader = PackageLoader("cherrydoor", "templates")
    setup_jinja2(app, loader=jinja2_loader, auto_reload=True)
    get_env(app).globals["sri"] = sri_for
    get_env(app).globals["csrf_field_name"] = CSRF_FIELD_NAME
    get_env(app).filters["vue"] = vue
    setup_routes(app)
    sio.attach(app)
    app.on_startup.append(setup_socket_tasks)

    return app


def setup_static_routes(app):
    app.router.add_static(
        "/static/",
        path=f"{os.path.dirname(os.path.realpath(__file__))}/static",
        name="static",
        append_version=True,
        follow_symlinks=True,
    )
    app["static_root_url"] = "/static"


def setup_routes(app):
    app.add_routes(views)


@contextfunction
def sri_for(context: Dict[str, Any], static_file_path: str) -> str:
    input_file = (
        f"{os.path.dirname(os.path.realpath(__file__))}/static/{static_file_path}"
    )
    sha256_hasher = sha256()
    with open(input_file, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256_hasher.update(data)
    sha256_hash = sha256_hasher.digest()
    hash_base64 = base64.b64encode(sha256_hash).decode()
    return f"sha256-{hash_base64}"


def vue(item):
    """
    Filter out vue templates
    For example: {{ "message.text" | vue }} will be transformed to just {{ "message.text" }}
    """
    return f"{{{{ {item} }}}}"
