"""
Set up security headers
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.7"
__status__ = "Prototype"
from uuid import uuid4
from copy import deepcopy
from base64 import b64encode

from aiohttp.web import middleware
from aiohttp_jinja2 import get_env
from secure import SecureHeaders, SecurePolicies


def setup(app):
    csp_value = (
        SecurePolicies.CSP()
        .default_src(SecurePolicies.CSP().Values.none)
        .base_uri(SecurePolicies.CSP().Values.self_)
        .block_all_mixed_content()
        .connect_src(SecurePolicies.CSP().Values.self_)
        .frame_src(SecurePolicies.CSP().Values.none)
        .img_src(SecurePolicies.CSP().Values.self_, "data:", "https:")
        .font_src(
            SecurePolicies.CSP().Values.self_,
            "https://fonts.gstatic.com/s/",
            "https://fonts.googleapis.com/css2",
        )
        .manifest_src(SecurePolicies.CSP().Values.self_)
        .worker_src(SecurePolicies.CSP().Values.self_, "blob:")
    )
    feature_value = (
        SecurePolicies.Feature()
        .geolocation(SecurePolicies.Feature.Values.none)
        .vibrate(SecurePolicies.Feature.Values.none)
    )
    if app["config"].get("https", False):
        csp_value = csp_value.upgrade_insecure_requests()
        hsts_value = (
            SecurePolicies.HSTS()
            .include_subdomains()
            .preload()
            .max_age(SecurePolicies.Seconds.one_month)
        )
    else:
        hsts_value = None
    if app["config"].get("sentry_csp_url", False):
        csp_value = csp_value.report_uri(app["config"]["sentry_csp_url"])
    else:
        csp_value = csp_value.report_uri("/csp")
    xxp_value = SecurePolicies.XXP().enabled_block()

    xfo_value = SecurePolicies.XFO().deny()

    referrer_value = SecurePolicies.Referrer().no_referrer()

    cache_value = SecurePolicies.Cache().no_store().must_revalidate().proxy_revalidate()

    app["secure_headers"] = SecureHeaders(
        csp=csp_value,
        hsts=hsts_value,
        xfo=xfo_value,
        xxp=xxp_value,
        referrer=referrer_value,
        feature=feature_value,
        cache=cache_value,
    )


@middleware
async def set_secure_headers(request, handler):
    nonce = b64encode(uuid4().bytes).decode("utf-8")
    script_src = [
        SecurePolicies.CSP().Values.self_,
        "blob:",
        #   SecurePolicies.CSP().Values.nonce(nonce),
        f"'nonce-{nonce}'",
        "https://unpkg.com",
        SecurePolicies.CSP().Values.unsafe_eval,
    ]
    style_src = [
        SecurePolicies.CSP().Values.self_,
        SecurePolicies.CSP().Values.unsafe_inline,
        "https://fonts.googleapis.com/css2",
    ]
    if request.path == "/api/v1/docs":
        script_src.append(SecurePolicies.CSP().Values.unsafe_inline)
        style_src.append(SecurePolicies.CSP().Values.unsafe_inline)
    get_env(request.app).globals["csp_nonce"] = nonce
    secure_headers = deepcopy(request.app["secure_headers"])
    secure_headers.csp.script_src(*script_src).style_src(*style_src)
    resp = await handler(request)
    secure_headers.aiohttp(resp)
    return resp
