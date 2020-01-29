#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""All website routes"""
# flak-related imports
from flask import render_template, url_for, request, session, redirect, flash, escape
from flask_login import current_user, login_user, logout_user, login_required

# import VerificationError thrown when password doesn't match the hash
from argon2.exceptions import VerificationError

from cherrydoor import app, mongo, hasher, LoginForm, login_manager, User, json

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.1.2"
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
    if form.validate_on_submit():
        login_username = mongo.users.find_one(
            {"username": escape(str(form.username.data))}
        )
        if login_username:
            try:
                if login_username["password"] != "" and hasher.verify(
                    login_username["password"].encode("utf-8"),
                    escape(form.password.data).encode("utf-8"),
                ):
                    user_obj = User(username=escape(form.username.data))
                    login_user(user_obj, remember=escape(form.remember.data))
                    # if login was succesful - redirect user to the dashboard
                    return redirect(url_for("index"))
                else:
                    error = " is-invalid"
            # if argon2 throws VerificationError it means the password doesn't match the hash for this username
            except (VerificationError, KeyError):
                error = " is-invalid"
        # if there is no user with this username, return Invalid username.
        else:
            error = " is-invalid"
    else:
        error = ""
    return render_template("login.html", form=form, error=error)


@app.route("/register", methods=["POST", "GET"])
@login_required
def register():
    # register an user on a POST request
    if request.method == "POST":
        # check if username and password were passed to this function
        try:
            username = escape(request.form["username"])
            password = escape(request.form["pass"].encode("utf-8"))
        except:
            return "No username or password specified", 400
        # check if an user with this username exists
        existing_user = mongo.users.find_one({"username": username})
        # if not - register him
        if not existing_user:
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
            # redirect user back to index
            return redirect(url_for("index"))
        else:
            # if the user exists - return a 401 message with that information
            return {"error": "That username already exists!"}, 401
    # render the registration form on a GET request
    return render_template("register.html")


@app.route("/csp-reports", methods=["POST"])
def csp():
    open("csp-logs.json", "a").close()
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
