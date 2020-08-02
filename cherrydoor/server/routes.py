#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""All website routes"""
# flak-related imports
from flask import render_template, url_for, request, session, redirect, flash, escape
from flask_login import current_user, login_user, logout_user, login_required

# import VerificationError thrown when password doesn't match the hash
from argon2.exceptions import VerificationError

from cherrydoor.server import app, db, hasher, LoginForm, login_manager, User, json

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b0"
__status__ = "Prototype"

# dashboard page
@app.route("/")
@login_required
def index():
    return render_template("index.html")


# login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # initiate form
    form = LoginForm()
    # if form wasn't validated, render login page without error indication
    if not form.validate_on_submit():
        return render_template("login.html", form=form, error="")
    try:
        # escape username and password
        username = escape(form.username.data)
        password = escape(form.password.data)
        user = db.users.find_one({"username": username})
        if not user:
            # if no user with selected is found raise VerificationError to return the template with error on inputs
            raise VerificationError
        validate = hasher.verify(
            user["password"].encode("utf-8"), password.encode("utf-8")
        )
        # if argon2 throws VerificationError it means the password doesn't match the hash for this username
        if user["password"] != "" and validate:
            user_obj = User(username=username)
            login_user(user_obj, remember=escape(form.remember.data))
            # if login was succesful - redirect user to the dashboard
            return redirect(url_for("index"))
    except (VerificationError, KeyError):
        pass
    return render_template("login.html", form=form, error=" is-invalid")


@app.route("/register", methods=["POST", "GET"])
@login_required
def register():
    # render the registration form if the request type isn't POST
    if request.method != "POST":
        return render_template("register.html")
    # otherwise check if username and password were passed to this function
    try:
        username = escape(request.form["username"])
        password = escape(request.form["pass"].encode("utf-8"))
    except:
        return "No username or password specified", 400
    # check if an user with this username exists
    existing_user = db.users.find_one({"username": username})
    # if the user exists - return a 401 message with that information
    if existing_user:
        return {"error": "That username already exists!"}, 401
    # if not - register him
    try:
        # if a card id was passed along - create a cards variable with it
        cards = [escape(request.form["card"])]
    except KeyError:
        # if not - make it empty
        cards = []
    # hash the password
    hashpass = hasher.hash(password)
    # insert the user to database
    users.insert({"username": username, "password": hashpass, "cards": cards})
    # log the user in
    user_obj = User(username=username)
    login_user(user_obj, remember=False)
    # redirect user to index
    return redirect(url_for("index"))


@app.route("/csp-reports", methods=["POST"])
def csp():
    try:
        open("csp-logs.json", "a").close()
    except PermissionError:
        return
    with open("csp-logs.json", "r+", encoding="utf-8") as f:

        try:
            logs = json.load(f)
        except json.decoder.JSONDecodeError:
            logs = {"logs": []}
        try:
            logs["logs"].append(json.loads(request.data.decode("utf-8")))
            f.seek(0, 0)
            json.dump(logs, f)
        except:
            return None, 400
    return None, 201


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("login"))
