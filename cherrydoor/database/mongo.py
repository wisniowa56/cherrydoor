import datetime as dt
from math import ceil

from bson.objectid import ObjectId
from bson import SON
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import WriteConcern, IndexModel, ASCENDING, DESCENDING, ReturnDocument

from cherrydoor.util import round_time


def init_db(config, loop):
    db = AsyncIOMotorClient(
        f"mongodb://{config.get('mongo', {}).get('url', 'localhost:27017')}/{config.get('mongo', {}).get('name', 'cherrydoor')}",
        username=config.get("mongo", {}).get("username", None),
        password=config.get("mongo", {}).get("password", None),
        io_loop=loop,
    )[config.get("mongo", {}).get("name", "cherrydoor")]
    return db


async def setup_db(app):
    user_indexes = [
        IndexModel([("username", ASCENDING)], name="username_index", unique=True),
        IndexModel([("cards", ASCENDING)], name="cards_index", sparse=True),
        IndexModel([("tokens.token", ASCENDING)], name="token_index", sparse=True),
    ]
    await app["db"].users.create_indexes(user_indexes)


async def close_db(app):
    app["db"].close()


async def list_permissions(app, username):
    user = await app["db"].users.find_one(
        {"username": username}, {"permissions": 1, "_id": 0}
    )
    if user != None:
        return user.get("permissions", [])
    else:
        return []


async def user_exists(app, username):
    count = app["db"].users.count_documents({"username": username})
    return count > 0


async def create_user(app, username, hashed_password=None, permissions=[], cards=[]):
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
    await app["db"].users.update_one(
        {"_id": ObjectId(identity)}, {"$set": {"password": new_password_hash}}
    )


async def add_token_to_user(app, identity, token_name, token):
    await app["db"].users.update_one(
        {"_id": ObjectId(identity)},
        {"$addToSet": {"tokens": {"name": token_name, "token": token}}},
    )


async def find_user_by_uid(app, identity, fields=["username"]):
    return await find_user_by(app, "_id", ObjectId(identity), fields)


async def find_user_by_username(app, username, fields=["_id"]):
    return await find_user_by(app, "username", username, fields)


async def find_user_by_token(app, token, fields=["username"]):
    return await find_user_by(app, "tokens.token", token, fields)


async def find_user_by_cards(app, cards, fields=["username"]):
    if not isinstance(cards, list):
        cards = [cards]
    projection = {}
    for field in fields:
        projection[field] = 1
    if "_id" not in fields:
        projection["_id"] = 0
    return await app["db"].users.find_one({"cards": cards}, projection)


async def find_user_by(app, search_fields, values, return_fields):
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
            if uid != None
            else "username": uid
            if uid != None
            else current_username
        },
        pipeline,
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


# async def add_api_open_to_logs(app, )


async def user_exists(app, **kwargs):
    return (
        app["db"].users.count_documents({key: value for key, value in kwargs.items()})
        > 0
    )


async def delete_user(app, uid=None, username=None):
    if uid:
        return await app["db"].users.delete_one({"_id": uid})

    elif username:
        return await app["db"].users.delete_one({"username": username})
    else:
        return False


async def add_cards_to_user(app, uid, cards):
    user = await app["db"].find_one_and_update(
        {"_id": uid},
        {"$addToSet": {"cards": {"$each": cards}}},
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


async def delete_cards_from_user(app, uid, cards):
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
    projection = {}
    for field in return_fields:
        projection[field] = 1
    if "_id" not in return_fields:
        projection["_id"] = 0
    return app["db"].users.find({}, projection=projection)


async def set_default_permissions(app, username):
    user = await app["db"].users.find_one_and_update(
        {"username": username},
        {"$set": {"permissions": ["enter"]}},
        projection={"_id": 0, "username": 1, "permissions": 1, "cards": 1},
        return_document=ReturnDocument.AFTER,
    )
    return user


async def get_settings(app):
    breaks = (await app["db"].settings.find_one({"setting": "break_times"})).get(
        "value", []
    )
    return {"breaks": breaks}


async def save_settings(app, settings):
    # TODO optimize into a single query
    for setting, value in settings.items():
        await app["db"].settings.find_one_and_update(
            {"setting": setting}, {"$set": {"value": value}}
        )
