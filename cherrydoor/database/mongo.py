"""Functions to simplify interacting with database."""
import datetime as dt
from math import ceil

from bson.objectid import ObjectId
from bson import SON
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import WriteConcern, IndexModel, ASCENDING, ReturnDocument


def init_db(config, loop):
    """Initiate the database connection.

    Parameters
    ----------
    config : AttrDict
        The app configuration
    loop : asyncio.AbstractEventLoop
        The event loop to use for database connection
    Returns
    -------
    db : motor.motor_asyncio.AsyncIOMotorClient
        The database connection object
    """
    db = AsyncIOMotorClient(
        f"mongodb://{config.get('mongo', {}).get('url', 'localhost:27017')}/{config.get('mongo', {}).get('name', 'cherrydoor')}",
        username=config.get("mongo", {}).get("username", None),
        password=config.get("mongo", {}).get("password", None),
        io_loop=loop,
    )[config.get("mongo", {}).get("name", "cherrydoor")]
    return db


async def setup_db(app):
    """Set up database indexes and collections.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    """
    user_indexes = [
        IndexModel([("username", ASCENDING)], name="username_index", unique=True),
        IndexModel([("cards", ASCENDING)], name="cards_index", sparse=True),
        IndexModel([("tokens.token", ASCENDING)], name="token_index", sparse=True),
    ]
    command_log_options = await app["db"].terminal.options()
    if (
        "capped" not in command_log_options
        or not command_log_options["capped"]
        or "timeseries" not in command_log_options
        or command_log_options["timeseries"]["timeField"] != "timestamp"
    ):
        await app["db"].drop_collection("terminal")
        await app["db"].create_collection(
            "terminal",
            size=app["config"].get("command_log_size", 100000000),
            capped=True,
            max=10000,
#             timeseries={
#                 "timeField": "timestamp",
#                 "metaField": "command",
#                 "granularity": "seconds",
#             },
#             expireAfterSeconds=app["config"].get(
#                 "command_log_expire_after", 604800
#             ),
        )
    await app["db"].users.create_indexes(user_indexes)


async def close_db(app):
    """Close the database connection.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    """
    app["db"].close()


async def list_permissions(app, username):
    """List the permissions for a user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    username : str
        The username of the user
    Returns
    -------
    permissions : list
        The list of permissions user has
    """
    user = await app["db"].users.find_one(
        {"username": username}, {"permissions": 1, "_id": 0}
    )
    if user is not None:
        return user.get("permissions", [])
    return []


async def user_exists(app, username):
    """Check if a user exists by username.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    username : str
        The username of the user
    Returns
    -------
    exists : bool
        True if the user exists, False otherwise
    """
    count = app["db"].users.count_documents({"username": username})
    return count > 0


async def create_user(
    app, username, hashed_password=None, permissions=None, cards=None
):
    """Create a single new user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    username : str
        The username for the new user
    hashed_password : str
        The argon2id hashed password for the new user
    permissions : list
        The list of permissions the new user will have
    cards : list
        The list of cards assigned to the new user
    Returns
    -------
    uid : str
        The uid of the new user
    """
    permissions = permissions if permissions else []
    cards = cards if cards else []
    result = (
        await app["db"]
        .users.with_options(write_concern=WriteConcern(w="majority"))
        .insert_one(
            {
                "username": username,
                "password": hashed_password,
                "permissions": permissions,
                "cards": cards,
            }
        )
    )
    return str(result.inserted_id)


async def change_user_password(app, identity, new_password_hash):
    """Change user's password.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    identity : str
        The uid of the user whose password is to be changed
    new_password_hash : str
        The new argon2id hashed password
    """
    await app["db"].users.update_one(
        {"_id": ObjectId(identity)}, {"$set": {"password": new_password_hash}}
    )


async def add_token_to_user(app, identity, token_name, token):
    """Assign an API token to a user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    identity : str
        The uid of the user to whom the token is to be assigned
    token_name : str
        The frontend name of the token to be assigned
    token : str
        The branca token to be assigned
    """
    await app["db"].users.update_one(
        {"_id": ObjectId(identity)},
        {"$addToSet": {"tokens": {"name": token_name, "token": token}}},
    )


async def find_user_by_uid(app, identity, fields=["username"]):
    """Find a user by their uid.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    identity : str
        The uid to search for
    fields : list, default=["username"]
        The fields to be returned in the user document
    Returns
    -------
    user : dict
        The user document
    """
    return await find_user_by(app, "_id", ObjectId(identity), fields)


async def find_user_by_username(app, username, fields=["_id"]):
    """Find a user by their username.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    username : str
        The username to search for
    fields : list, default=["_id"]
        The fields to be returned in the user document
    Returns
    -------
    user : dict
        The user document
    """
    return await find_user_by(app, "username", username, fields)


async def find_user_by_token(app, token, fields=["username"]):
    """Find a user by an API token assigned to them.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    token : str
        The API token to search for
    fields : list, default=["username"]
        The fields to be returned in the user document
    Returns
    -------
    user : dict
        The user document
    """
    return await find_user_by(app, "tokens.token", token, fields)


async def find_user_by_cards(app, cards, fields=["username"]):
    """Find a user by a list of cards assigned to them.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    cards : list
        The list of cards to search for
    fields : list, default=["username"]
        The fields to be returned in the user document
    Returns
    -------
    user : dict
        The user document
    """
    if not isinstance(cards, list):
        cards = [cards]
    projection = {}
    for field in fields:
        projection[field] = 1
    if "_id" not in fields:
        projection["_id"] = 0
    return await app["db"].users.find_one({"cards": cards}, projection)


async def find_user_by(app, search_fields, values, return_fields):
    """Find a user by arbritary search fields.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    search_fields : list
        The fields to search for
    values : list
        The values to search for
    return_fields : list
        The fields to return in the user document
    Returns
    -------
    user : dict
        The user document
    """
    if not isinstance(search_fields, list):
        search_fields = [search_fields]
    if not isinstance(values, list):
        values = [values]
    if "api_key" in search_fields:
        search_fields[search_fields.index("api_key")] = "tokens.token"
    projection = {}
    for field in return_fields:
        projection[field] = 1
    if "_id" not in return_fields:
        projection["_id"] = 0
    user = await app["db"].users.find_one(
        SON(dict(zip(search_fields, values))), projection=projection
    )
    return user


#
async def get_grouped_logs(app, datetime_from, datetime_to, granularity):
    """Get logs between two datetimes.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    datetime_from : datetime.datetime
        The start datetime
    datetime_to : datetime.datetime
        The end datetime
    granularity : str
        The granularity of the logs to be returned
    Returns
    -------
    logs : list
        The list of logs between the two datetimes with a given granularity
    """
    if not isinstance(granularity, dt.timedelta):
        granularity = dt.timedelta(seconds=granularity)
    boundries = [
        datetime_from + granularity * i
        for i in range(ceil((datetime_to - datetime_from) / granularity))
    ]
    boundries[-1] = datetime_to + dt.timedelta(seconds=1)
    pipeline = [
        {"$match": {"timestamp": {"$gte": datetime_from, "$lte": datetime_to}}},
        {
            "$project": {
                "timestamp": 1,
                "successful": {"$toInt": "$success"},
                "during_break": {
                    "$toInt": {"$eq": ["$auth_mode", "Manufacturer code"]}
                },
            }
        },
        {
            "$bucket": {
                "groupBy": "$timestamp",
                "boundaries": boundries,
                "default": "no_match",
                "output": {
                    "count": {"$sum": 1},
                    "successful": {"$sum": "$successful"},
                    "during_break": {"$sum": "$during_break"},
                },
            }
        },
    ]
    logs = []
    async for doc in app["db"].logs.aggregate(pipeline):
        logs.append(
            {
                "date_from": doc["_id"].isoformat(),
                "date_to": (doc["_id"] + granularity).isoformat(),
                "count": doc["count"],
                "successful": doc["successful"],
                "during_break": doc["during_break"],
            }
        )

    return logs


async def modify_user(app, uid=None, current_username=None, **kwargs):
    """Change user's properties.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    uid : str, default=None
        The uid of the user to be modified
    current_username : str, default=None
        The current username of the user
    **kwargs : dict
        The properties to be changed.
        username will override the current username
        cards will override the current card list
        permissions will override the current permissions
        card will add a card to the user's card list
        permission will add a permission to the user's permissions
    Returns
    -------
    user : dict
        The user document
    """
    overwrite_keys = ["username", "cards", "permissions"]
    append_keys = ["card", "permission"]
    pipeline = []
    if bool(set(overwrite_keys) & set(kwargs.keys())):
        pipeline.append(
            {
                "$set": {
                    key: value
                    for key, value in kwargs.items()
                    if key in overwrite_keys and len(value) > 0
                }
            }
        )
    if bool(set(append_keys) & set(kwargs.keys())):
        pipeline.append(
            {
                "$set": {
                    key: {"$concatArrays": [f"${key}", [value]]}
                    for key, value in kwargs.items()
                    if key in append_keys and len(value) > 0
                }
            }
        )
    if len(pipeline) <= 0:
        return None
    user = await app["db"].users.find_one_and_update(
        {
            "_id"
            if uid is not None
            else "username": uid
            if uid is not None
            else current_username
        },
        pipeline,
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


# async def add_api_open_to_logs(app, )


async def user_exists(app, **kwargs):
    """Check if a user exists by arbitrary keys.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    **kwargs : dict
        The properties and values to be seached for
    Returns
    -------
    exists : bool
        True if the user exists, False otherwise
    """
    return app["db"].users.count_documents(kwargs) > 0


async def delete_user(app, uid=None, username=None):
    """Delete a specified user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    uid : str, default=None
        The uid of the user to be deleted. If None will use username
    username : str, default=None
        The username of the user to be deleted if no uid is specified.
        If also None won't delete anything.
    Returns
    -------
    deleted : bool
        True if the user was deleted, False otherwise
    """
    if uid:
        return await app["db"].users.delete_one({"_id": uid})

    if username:
        return await app["db"].users.delete_one({"username": username})
    return False


async def add_cards_to_user(app, uid, cards):
    """Add cards to a user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    uid : str
        The uid of the user to add cards to
    cards : list
        The cards to be added to the user
    Returns
    -------
    user : dict
        The modified user document
    """
    user = await app["db"].find_one_and_update(
        {"_id": uid},
        {"$addToSet": {"cards": {"$each": cards}}},
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


async def delete_cards_from_user(app, uid, cards):
    """Delete specified cards from a user.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    uid : str
        The uid of the user to delete cards from
    cards : list
        The cards to be deleted from the user
    Returns
    -------
    user : dict
        The modified user document
    """
    if not isinstance(cards, list):
        cards = [cards]
    user = await app["db"].users.find_one_and_update(
        {"_id": uid},
        {"$pullAll": {"cards": cards}},
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


async def create_users(app, users):
    """Create multiple users.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    users : list
        A list of dictionaries with user data to be created
    """
    return (
        await app["db"]
        .users.with_options(write_concern=WriteConcern(w="majority"))
        .insert_many(
            [
                {
                    "username": user.get("username"),
                    "password": user.get("password", None),
                    "permissions": user.get("permissions", []),
                    "cards": user.get("cards", []),
                }
                for user in users
            ]
        )
    )


async def get_users(app, return_fields=["username", "permissions", "cards"]):
    """Retrieve all users from the database.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    return_fields : list, default=["username", "permissions", "cards"]
        The fields to be returned for each user.
    Returns
    -------
    users : list
        A list of user documents
    """
    projection = {}
    for field in return_fields:
        projection[field] = 1
    if "_id" not in return_fields:
        projection["_id"] = 0
    return app["db"].users.find({}, projection=projection)


async def set_default_permissions(app, username):
    """Set user permissions to the default ("enter").

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    username : str
        The username of the user to be modified
    Returns
    -------
    user : dict
        The modified user document with usernae, permissions and cards fields
    """
    user = await app["db"].users.find_one_and_update(
        {"username": username},
        {"$set": {"permissions": ["enter"]}},
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


async def get_settings(app):
    """Retrieve breaks settings from the database.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    Returns
    -------
    breaks : dict
        A dictionary with the breaks settings
    """
    breaks = (await app["db"].settings.find_one({"setting": "break_times"})).get(
        "value", []
    )
    return {"breaks": breaks}


async def save_settings(app, settings):
    """Save settings to the database.

    Parameters
    ----------
    app : aiohttp.web.Application
        The aiohttp application instance
    settings : dict
        A dictionary with all settings to set
    """
    # TODO optimize into a single query
    for setting, value in settings.items():
        await app["db"].settings.find_one_and_update(
            {"setting": setting}, {"$set": {"value": value}}
        )
