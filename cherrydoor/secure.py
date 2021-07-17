"""Set up security headers."""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"
from uuid import uuid4
from copy import deepcopy
from base64 import b64encode

from aiohttp.web import middleware
from aiohttp_jinja2 import get_env
import secure


def setup(app):
    """Set secure headers values.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance.
    """
    server = secure.Server().set("Secure")
    csp_value = (
        secure.ContentSecurityPolicy()
        .default_src("'none'")
        .base_uri("'self'")
        .connect_src("'self'")
        .frame_src("'none'")
        .img_src("'self'", "data:", "https:")
        .font_src(
            "'self'",
            "https://fonts.gstatic.com/s/",
            "https://fonts.googleapis.com/css2",
        )
        .manifest_src("'self'")
        .worker_src("'self'", "blob:")
    )
    # feature_value = secure.PermissionsPolicy().geolocation("'none'").vibrate("'none'")
    if app["config"].get("https", False):
        csp_value = csp_value.upgrade_insecure_requests()
        hsts_value = (
            secure.StrictTransportSecurity()
            .include_subdomains()
            .preload()
            .max_age(2592000)
        )
    else:
        hsts_value = None
    if app["config"].get("sentry_csp_url", False):
        csp_value = csp_value.custom_directive(
            "report-uri", app["config"]["sentry_csp_url"]
        )
    else:
        csp_value = csp_value.custom_directive("report-uri", "/csp")

    xfo_value = secure.XFrameOptions().deny()

    referrer_value = secure.ReferrerPolicy().no_referrer()

    cache_value = secure.CacheControl().no_store().must_revalidate().proxy_revalidate()

    app["secure_headers"] = secure.Secure(
        server=server,
        csp=csp_value,
        hsts=hsts_value,
        xfo=xfo_value,
        referrer=referrer_value,
        # permissions=feature_value,
        cache=cache_value,
    )


@middleware
async def set_secure_headers(request, handler):
    """Add secure headers to requests.

    Parameters
    ----------
    request : aiohttp.web.Request
        The request to set secure headers on.
    handler : function
        The middleware handler function.
    Returns
    -------
    aiohttp.web.Response
        The modified response to the request.
    """
    nonce = b64encode(uuid4().bytes).decode("utf-8")
    script_src = [
        "'self'",
        "blob:",
        #   SecurePolicies.CSP().Values.nonce(nonce),
        f"'nonce-{nonce}'",
        "https://unpkg.com",
        "'unsafe-eval'",
    ]
    style_src = [
        "'self'",
        "'unsafe-inline'",
        "https://fonts.googleapis.com/css2",
    ]
    if request.path == "/api/v1/docs":
        script_src[2] = "'unsafe-inline'"
        style_src.append("'unsafe-inline'")
    get_env(request.app).globals["csp_nonce"] = nonce
    secure_headers = deepcopy(request.app["secure_headers"])
    secure_headers.csp.script_src(*script_src).style_src(*style_src)
    resp = await handler(request)
    secure_headers.framework.aiohttp(resp)
    return resp
