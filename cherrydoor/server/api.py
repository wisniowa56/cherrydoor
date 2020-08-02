#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""All REST API routes and functions"""
from cherrydoor.server import (
    api,
    Resource,
    current_user,
    parser,
    dt,
    inputs,
    db,
    escape,
)

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b0"
__status__ = "Prototype"

parser.add_argument("time_from", help="start of time range")
parser.add_argument("time_to", help="end of time range")
parser.add_argument("username", help="username of requested user")
parser.add_argument("card", help="MiFare card uid")


class Stats(Resource):
    """
	Usage statistics. Accesible on `/api/stats` and `/api/stats/<string:time_from>/<string:time_to>` endpoint
	"""

    def get(self, time_from=None, time_to=None):
        """
		If http GET is used, the api will return list of logs with range determined by request parameters `time_from` and `time_to` or in url (iso8601 formatted).
		When no parameters are present, this method will retuen logs between 7 days ago and today
		Logs are retrived from `logs` collection and need to contain `timestamp` field with a valid datetime as a value.
		"""
        if not current_user.is_authenticated:
            return {"error": "Not Authenticated"}, 401
        params = parser.parse_args()
        try:
            time_from = inputs.datetime_from_iso8601(escape(time_from))
            time_to = inputs.datetime_from_iso8601(escape(time_to))
        except AttributeError:
            try:
                time_from = inputs.datetime_from_iso8601(escape(params["time_from"]))
            except (AttributeError, KeyError):
                time_from = dt.date.today() - dt.timedelta(days=7)
            try:
                time_to = inputs.datetime_from_iso8601(escape(params["time_to"]))
            except (AttributeError, KeyError):
                time_to = dt.datetime.now()
        try:
            results = [
                result
                for result in db.logs.find(
                    {"timestamp": {"$lt": time_to, "$gte": time_from}},
                    {"card": 0, "_id": 0},
                )
            ]
            return results, 200
        except:
            return [], 404


class Card(Resource):
    """
	Card management and retrival. Accesible on `/api/card/<card>` and `/api/card` endpoints.
	"""

    def __init__(self):
        """
		error messages
		"""
        self.card_error = {
            "error": "no card specified. Pass card uid in url or as `card` in request body"
        }
        self.auth_error = {"error": "Not Authenticated"}

    def check_params(self, card=None, params=None):
        """
		Helper function that returns card and username from params and url - if they are there
		"""
        # if there is no card in url, try to get it from request body
        if not card:
            card = params["card"]
            if not card:
                raise KeyError
        card = escape(card.upper())
        # try to get username from request body
        try:
            username = escape(params["username"])
        except KeyError:
            username = None
        return card, username

    def get(self, card=None):
        """
		Used when HTTP GET request is recieved
		This function checks if the card uid is associated with any user
		UID can be a part of url (/api/card/<uid>) or be passed in request body
		"""
        # check if request was made by a logged-in user
        if not current_user.is_authenticated:
            # return error 401 and explanation if that's not the case
            return self.auth_error, 401
        # get arguments from request body
        params = parser.parse_args()
        # make sure card was passed and is a valid uppercase string
        # additionally, get username if it was passed in request body
        try:
            card, username = self.check_params(card, params)
        except KeyError:
            # if there is no card at all, return a 400 error with an explanation message
            return (self.card_error, 400)
        if username:
            # if username was passed with the request body, only check that user or return 404 if he doesn't exist
            result = db.users.find_one_or_404(
                {"username": username, "cards": card}, {"password": 0, "_id": 0}
            )
        else:
            # if no username was passed, check if any user has this card
            result = db.users.find_one_or_404(
                {"cards": card}, {"password": 0, "_id": 0}
            )
        # return the result and status code 200
        return result, 200

    def post(self, card=None):
        """
		If HTTP POST is used, add the card to a user.
		User is determined by `username` passed in request body.
		If there is no `username` present, current user is modified.
		"""
        # check if request was made by a logged-in user
        if not current_user.is_authenticated:
            # return error 401 and explanation if that's not the case
            return self.auth_error, 401
        # get arguments from request body
        params = parser.parse_args()
        # make sure card was passed and is a valid uppercase string
        # additionally, get username if it was passed in request body
        try:
            card, username = self.check_params(card, params)
        except KeyError:
            # if there is no card at all, return a 400 error with an explanation message
            return (self.card_error, 400)
        if username:
            # if username was passed with the request body, add the card to that user
            db.users.find_one_and_update(
                {"username": username}, {"$push": {"cards": card}}
            )
        else:
            # if no username was passed, add the card to current user
            current_user.add_card(card)
        # return true and 201 status on completion
        return True, 201

    def delete(self, card=None):
        """
		If HTTP DELETE is used, delete the card from database of users.
		User is determined by `username` passed in request body.
		If there is no `username` present, card will be removed from any and all users that it's associated with.
		If `*` is passed as username, returns all users.
		"""
        if not current_user.is_authenticated:
            return self.auth_error, 401
        params = parser.parse_args()
        # make sure card was passed and is a valid uppercase string.
        # additionally, get username if it was passed in request body
        try:
            card, username = self.check_params(card, params)
        except KeyError:
            # if there is no card at all, return a 400 error with an explanation message
            return (self.card_error, 400)
        if username:
            db.users.find_one_and_update(
                {"username": username}, {"$pull": {"cards": card}}
            )
        else:
            db.users.update({}, {"$pull": {"cards": card}})
        return True, 200


class UserAPI(Resource):
    """
	User data management and retrieval. Accesible on `api/user/<username>` and `/api/user` endpoints.
	"""

    def __init__(self):
        """
		error messages
		"""
        self.username_error = {
            "error": "no username specified. Pass username in url or as `username` in request body"
        }
        self.auth_error = {"error": "Not Authenticated"}

    def check_username(self, username, params):
        """
		Helper function for getting and validating username from url or request body
		"""
        if not username:
            params = parser.parse_args()
            username = escape(params["username"])
            if username == None:
                raise KeyError
        username = escape(username)
        return username

    def get(self, username=None):
        """
		If HTTP GET is used, see if user with username passed in url or in request body (as `username`) exists and return their username and cards associated with them.
		When no user with request username exists, return 404 status code
		"""
        if not current_user.is_authenticated:
            return self.auth_error, 401
        params = parser.parse_args()
        try:
            username = self.check_username(username, params)
        except KeyError:
            return (self.username_error, 400)
        if username == "*":
            result = list(db.users.find({}, {"password": 0, "_id": 0}))
        else:
            result = db.users.find_one_or_404(
                {"username": username}, {"password": 0, "_id": 0}
            )
        return result, 200

    def post(self, username=None):
        """
		If HTTP POST is used, create a passwordless user (unable to manage the door, able to enter)
		"""
        if not current_user.is_authenticated:
            return self.auth_error, 401
        params = parser.parse_args()
        try:
            username = self.check_username(username, params)
        except KeyError:
            return (self.username_error, 400)
        try:
            card = escape(params["card"].upper())
            if not card:
                raise KeyError
        except KeyError:
            card = ""
        db.users.update_one(
            {"username": username},
            {"$set": {"username": username, "cards": [card]}},
            upsert=True,
        )
        return None, 201

    def delete(self, username=None):
        """
		If HTTP DELETE is used, delete the specified user
		"""
        if not current_user.is_authenticated:
            return self.auth_error, 401
        params = parser.parse_args()
        try:
            username = self.check_username(username, params)
        except KeyError:
            return (self.username_error, 400)
        db.users.delete_one({"username": username})
        return None, 204


api.add_resource(Stats, "/api/stats", "/api/stats/<string:time_from>/<string:time_to>")
api.add_resource(UserAPI, "/api/user/<string:username>", "/api/user")
api.add_resource(Card, "/api/card/<string:card>", "/api/card")
