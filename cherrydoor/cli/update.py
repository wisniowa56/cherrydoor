from glob import iglob
from importlib import import_module, invalidate_caches
from importlib.util import find_spec
from os.path import basename
from subprocess import check_call  # nosec
from sys import executable

from packaging.version import parse as parse_version

from cherrydoor.config import load_config


def step_enabled(step, args):
    return step not in args.update_steps_excluded and (
        args.update_steps == [] or step in args.update_steps
    )


def pip_update(dev=False):
    command = [executable, "-m", "pip", "install", "-U", "Cherrydoor"]
    if dev:
        command.append("--pre")
    check_call(command)  # nosec - this is a safe use of check_call
    invalidate_caches()


def update(args, config={}):
    if config == {}:
        config = load_config(args)[0]
    previous_version = parse_version(
        import_module("cherrydoor.__version__").__version__
    )
    if step_enabled("pip", args):
        pip_update()
    current_version = parse_version(import_module("cherrydoor.__version__").__version__)
    database_enabled = step_enabled("database", args)
    if database_enabled:
        from pymongo import MongoClient

        db = MongoClient(
            f"mongodb://{config.get('mongo', {}).get('url', 'localhost:27017')}/{config.get('mongo', {}).get('name', 'cherrydoor')}"
        )[config.get("mongo", {}).get("name", "cherrydoor")]
        database_version = db.settings.find_one({"setting": "version"})
        if database_version == None:
            database_version = previous_version
    config_enabled = step_enabled("config", args)
    if config_enabled:
        config_version = parse_version(str(config.get("version", "")))
    path = find_spec("cherrydoor.cli.update_scripts").submodule_search_locations[0]
    for script_name in iglob(f"{path}/[a-zA-Z0-9]*.*py"):
        update_script = import_module(
            f"cherrydoor.cli.update_scripts.{basename(script_name)[:-3]}"
        )
        script_version = parse_version(update_script.__version__)

        if script_version > previous_version:
            try:
                update_script.update()
            except AttributeError:
                pass
        if database_enabled and script_version > database_version:
            try:
                update_script.update_database(db)
            except AttributeError:
                pass
        if config_enabled and script_version > config_version:
            try:
                update_script.update_config(config)
            except AttributeError:
                pass
