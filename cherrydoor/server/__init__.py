#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main cherydoor module file
Creates app, api, socket and db instances and imports all routes.
"""
# built-in libraries import:
import json
import datetime as dt
from hashlib import sha256, sha384
import base64
from pathlib import Path

# flask-connected imports:
from flask import Flask, escape, url_for
from flask_login import current_user, LoginManager, UserMixin
from flask_restful import Resource, Api, reqparse, inputs, abort
from flask_socketio import SocketIO, emit, disconnect
from flask_talisman import Talisman
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from werkzeug.middleware.proxy_fix import ProxyFix

# hashing function import:
from argon2 import PasswordHasher

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b0"
__status__ = "Prototype"
default_routes = [
    "config.json",
    "/var/cherrydoor/config.json",
    f"{Path.home()}/.config/cherrydoor/config.json",
]
for route in default_routes:
    try:
        # load configuration file from one of the default routes
        with open(route, "r", encoding="utf-8") as f:
            # convert confuguration to a dictionary using json.load()
            config = json.load(f)
            break
    except FileNotFoundError:
        # ignore if config wasn't found
        pass
if config == None:
    raise FileNotFoundError("No config.json found")


class LoginForm(FlaskForm):
    """create fields for login form with labels based on translations form config.json file"""

    username = StringField(
        config["login-translation"]["username"],
        validators=[DataRequired()],
        render_kw={"placeholder": config["login-translation"]["username"]},
    )
    password = PasswordField(
        config["login-translation"]["password"],
        validators=[DataRequired()],
        render_kw={"placeholder": config["login-translation"]["password"]},
    )
    remember = BooleanField(config["login-translation"]["remember-me"])
    submit = SubmitField(config["login-translation"]["log-in"])


# app creation
# create a Flask instance
app = Flask(__name__, template_folder="../templates", static_folder="../static")
# set up a secret key for cookie and session encryption based on config.json
app.config["SECRET_KEY"] = config["secret-key"]
app.config["TEMPLATES_AUTO_RELOAD"] = True
# pymongo connection
# configure database access uri
try:
    if config["mongo"]:
        from flask_pymongo import PyMongo

        app.config[
            "MONGO_URI"
        ] = f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}"
        try:
            # set up PyMongo using credentials from config.json
            db = PyMongo(
                app,
                username=config["mongo"]["username"],
                password=config["mongo"]["password"],
            ).db
        except KeyError:
            # if username or password aren't defined in config, don't use them at all
            db = PyMongo(app).db
        try:
            db.client.server_info()
        except Exception as e:
            print(
                f"Connection to MongoDB failed. Are you sure it's installed and correctly configured? Error: {e}"
            )
except KeyError:
    print("No supported database present in config.json")
# create login_manager for flask_login
login_manager = LoginManager()
# default view (page) used for logging in
login_manager.login_view = "login"
# set a better session protection
login_manager.session_protection = "strong"
# message shown to anonymous users when a page requires being logged in - set in config.json
login_manager.login_message = config["login-translation"]["message"]
# initialize the login_manager
login_manager.init_app(app)

# create an argon2 hasher instance that will be called for all future operations
hasher = PasswordHasher(
    time_cost=4,
    memory_cost=65536,
    parallelism=8,
    hash_len=16,
    salt_len=16,
    encoding="utf-8",
)

# create a restful api instance from flask_restful
api = Api(app)

# create a flask_restful request argument parser instance
parser = reqparse.RequestParser()

# create socketio instance
socket = SocketIO(app)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

csp = {
    "default-src": ["'none'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "font-src": ["'self'"],
    "img-src": ["'self'"],
    "connect-src": ["'self'"],
    "base-uri": ["'none'"],
    "form-action": ["'self'"],
    "require-sri-for": ["scripts", "styles"],
}
try:
    if config["https"]["enabled"]:
        csp.update({"block-all-mixed-content": [], "upgrade-insecure-requests": []})
except KeyError:
    pass
fp = {
    "accelerometer": "'none'",
    "ambient-light-sensor": "'none'",
    "autoplay": "'none'",
    "battery": "'none'",
    "camera": "'self'",
    "display-capture": "'none'",
    "document-domain": "'none'",
    "encrypted-media": "'none'",
    "execution-while-not-rendered": "'self'",
    "execution-while-out-of-viewport": "'self'",
    "fullscreen": "'self'",
    "geolocation": "'none'",
    "gyroscope": "'none'",
    "layout-animations": "'self'",
    "legacy-image-formats": "'self'",
    "magnetometer": "'none'",
    "microphone": "'none'",
    "midi": "'none'",
    "navigation-override": "'none'",
    "oversized-images": "'none'",
    "payment": "'none'",
    "picture-in-picture": "'none'",
    "publickey-credentials": "'self'",
    "speaker": "'self'",
    "sync-xhr": "'self'",
    "usb": "'none'",
    "vr": "'none'",
    "wake-lock": "'none'",
    "xr-spatial-tracking": "'none'",
}
try:
    Talisman(
        app,
        force_https=config["https"]["enabled"],
        force_https_permanent=config["https"]["enabled"],
        session_cookie_secure=config["https"]["enabled"],
        feature_policy=fp,
        content_security_policy=csp,
        content_security_policy_report_uri="/csp-reports",
        strict_transport_security=config["https"]["hsts-enabled"],
        strict_transport_security_preload=config["https"]["hsts-preload"],
        #        content_security_policy_nonce_in=["script-src", "style-src"],
        referrer_policy="no-referrer",
    )
except KeyError:
    Talisman(
        app,
        feature_policy=fp,
        content_security_policy=csp,
        content_security_policy_report_uri="/csp-reports",
    )


class User(UserMixin):
    """
    User class used by flask_login
    """

    def __init__(self, username):
        self.username = username

    @staticmethod
    def is_authenticated(self):
        """
        Authentication status
        """
        return True

    @staticmethod
    def is_active(self):
        """
        Shows that the user is logged in
        """
        return True

    @staticmethod
    def is_anonymous(self):
        """
        A logged in user is not anonymous
        """
        return False

    def get_id(self):
        """
        Returns the id - in this case username
        """
        return self.username

    def get_cards(self):
        """
        Returns all mifare card ids associated with the account
        """
        return db.users.find_one({"username": self.username}, {"_id": 0, "cards": 1})[
            "cards"
        ]

    def add_card(self, card):
        """
        Adds a mifare card id to user profile
        """
        db.users.update_one(
            {"username": self.username}, {"$push": {"cards": card}}, upsert=True
        )

    def delete_card(self, card):
        """
        Removes a mifare card id from user profile
        """
        db.users.update_one({"username": self.username}, {"$pull": {"cards": card}})

    def check_privilege(privilege="admin"):
        """
        Checks if the user has a specified privilege.
        Defaults to checking for administrative privileges
        """
        return (
            privilege
            in db.user.find_one(
                {"username": self.username}, {"_id": 0, "privileges": 1}
            )["privileges"]
        )

    def get_privileges():
        """
        Returns all privileges user has
        """
        return db.user.find_one(
            {"username": self.username}, {"_id": 0, "privileges": 1}
        )["privileges"]


@login_manager.user_loader
def load_user(username):
    """
    A function for loading users from database by username
    """
    u = db.users.find_one({"username": username})
    if not u:
        return None
    return User(username=u["username"])


def sri_for(endpoint, **values):
    input = url_for(endpoint, **values)
    input = input.replace(app.static_url_path, app.static_folder)
    hash = sha256()
    with open(input, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hash.update(data)
    hash = hash.digest()
    hash_base64 = base64.b64encode(hash).decode()
    return f"sha256-{hash_base64}"


app.jinja_env.globals["sri_for"] = sri_for

import cherrydoor.server.api
import cherrydoor.server.routes
import cherrydoor.server.websockets
