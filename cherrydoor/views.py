"""Pages visible to users."""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import aiohttp_jinja2
from aiohttp import web
from aiohttp_csrf import generate_token as generate_csrf_token
from aiohttp_security import check_authorized, check_permission, remember

from cherrydoor.auth import check_credentials, get_permissions
from cherrydoor.util import redirect

routes = web.RouteTableDef()


@routes.get("/", name="index")
@routes.get("/dashboard", name="dashboard")
@routes.get("/users", name="users")
@routes.get("/settings", name="settings")
@routes.get("/console", name="console")
@aiohttp_jinja2.template("index.html")
async def index(request: web.Request):
    """Render Main page. Jinja2 template is index.html.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request object
    Returns
    -------
    dict
        values injected to the template (permissions)
    Raises
    ------
    aiohttp.web.HTTPUnauthorized
        If the user is not logged in
    aiohttp.web.HTTPForbidden
        If the user is not authorized to access the dashboard
    """
    try:
        await check_permission(request, "dashboard")
    except web.HTTPUnauthorized:
        raise redirect(request.app.router, "login")
    except web.HTTPForbidden as e:
        raise e  # redirect(request.app.router, "")
    permissions = await get_permissions(request)
    return {"permissions": permissions}


@routes.view("/login", name="login")
class Login(web.View):
    """Login page.

    Methods
    -------
    get
        Render the login page
    post
        Attempt to login the user
    """

    @aiohttp_jinja2.template("login.html")
    async def get(self):
        """Render the login page. Jinja2 template is login.html.

        Returns
        -------
        dict
            values injected to the template (csrf token)
        """
        csrf_token = await generate_csrf_token(self.request)
        return {"csrf_token": csrf_token}

    @aiohttp_jinja2.template("login.html")
    async def post(self):
        """Attempt to login the user. Jinja2 template is login.html.

        Returns
        -------
        web.Response
            Redirect to the dashboard page or back to the login page
        """
        try:
            authorized = await check_authorized(self.request)
        except web.HTTPUnauthorized:
            authorized = False
        redirect_response = redirect(self.request.app.router, "index")
        if authorized:
            raise redirect_response
        form = await self.request.post()
        if not form.get("username", False) or not form.get("password", False):
            csrf_token = await generate_csrf_token(self.request)
            return {
                "no-username": not form.get("username", False),
                "no-password": not form.get("password", False),
                "csrf": csrf_token,
            }
        authorized, uid = await check_credentials(
            self.request.app, form["username"], form["password"]
        )
        if authorized:
            await remember(
                self.request,
                redirect_response,
                uid,
                remember=form.get("remember", False),
            )
            raise redirect_response
        csrf_token = await generate_csrf_token(self.request)
        return {"invalid_credentials": True, "csrf_token": csrf_token}
