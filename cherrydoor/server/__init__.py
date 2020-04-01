#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main cherydoor module file
Creates app, api, socket and db instances and imports all routes.
"""
# built-in libraries import:
import json
import datetime as dt

# flask-connected imports:
from flask import Flask, escape
from flask_login import current_user, LoginManager, UserMixin
from flask_restful import Resource, Api, reqparse, inputs, abort
from flask_socketio import SocketIO, emit, disconnect
from flask_talisman import Talisman
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired

# hashing function import:
from argon2 import PasswordHasher

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.4"
__status__ = "Prototype"
try:
    with open("config.json", "r", encoding="utf-8") as f:  # load configuration file
        config = json.load(f)  # convert confuguration to a dictionary using json.load()
except FileNotFoundError:
    # load configuration file from `/var/cherrydoor` if it exists
    with open("/var/cherrydoor/config.json", "r", encoding="utf-8") as f:
        # convert confuguration to a dictionary using json.load())
        config = json.load(f)


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


csp = {
    "default-src": ["'none'"],
    "script-src": ["'self'"],
    "style-src": ["'self'"],
    "font-src": ["'self'"],
    "img-src": ["'self'"],
    "connect-src": ["'self'"],
    "require-sri-for": ["script", "style"],
    "base-uri": ["'none'"],
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
        session_cookie_secure=config["https"]["enabled"],
        feature_policy=fp,
        content_security_policy=csp,
        content_security_policy_report_uri="/csp-reports",
        strict_transport_security=config["https"]["hsts-enabled"],
        strict_transport_security_preload=config["https"]["hsts-preload"],
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
        return db.users.find_one({"username": self.username})["cards"]

    def add_card(self, card):
        """
        adds a mifare card id to user profile
        """
        db.users.update_one(
            {"username": self.username}, {"$push": {"cards": card}}, upsert=True
        )

    def delete_card(self, card):
        """
        adds a mifare card id from user profile
        """
        db.users.update_one({"username": self.username}, {"$pull": {"cards": card}})


@login_manager.user_loader
def load_user(username):
    """
    A function for loading users from database by username
    """
    u = db.users.find_one({"username": username})
    if not u:
        return None
    return User(username=u["username"])


import cherrydoor.server.api
import cherrydoor.server.routes
import cherrydoor.server.websockets
