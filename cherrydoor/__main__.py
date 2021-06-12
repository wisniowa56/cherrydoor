#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the server"""

__author__ = "opliko"
__license__ = "MIT"
__status__ = "Prototype"

import argparse
import asyncio
import logging

from aiohttp import web

from cherrydoor.__version__ import __version__
from cherrydoor.config import add_args, load_config


def cherrydoor():
    parser = argparse.ArgumentParser(
        prog="cherrydoor", description="Cherrydoor management"
    )
    parser.add_argument(
        "-v",
        "--version",
        help="Print Cherrydoor version and exit",
        action="version",
        version=f"Cherrydoor {__version__}",
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    install_parser = subparsers.add_parser(
        "install", help="Install some possible requirements"
    )
    install_parser.set_defaults(install_steps_excluded=[], install_steps=[], fail=False)
    install_parser.add_argument(
        "--exit-on-fail",
        help="If any step fails, stop the installer",
        dest="fail",
        action="store_true",
    )
    install_steps_group = install_parser.add_argument_group(
        "steps",
        "installation steps you want to run (if none are selected all will be run)",
    )
    install_steps = {
        "dependencies": "install all dependencies that weren't installed with pip",
        "service": "set up a systemd unit file",
        "config": "create a config file",
        "database": "set up MongoDB user, collections, etc.",
        "user": "create a new administrator user",
    }
    for (step, description) in install_steps.items():
        install_steps_group.add_argument(
            f"--{step}",
            dest="install_steps",
            action="append_const",
            const=step,
            help=description,
        )
        install_steps_group.add_argument(
            f"--no-{step}",
            dest="install_steps_excluded",
            action="append_const",
            const=step,
            help=f"don't {description}",
        )
    update_parser = subparsers.add_parser(
        "update", help="update Cherrydoor to the newest version"
    )
    update_parser.set_defaults(update_steps_excluded=[], update_steps=[], fail=False)
    update_parser.add_argument(
        "-d",
        "--dev",
        help="Install latest development version",
        dest="dev",
        action="store_true",
    )
    update_parser.add_argument(
        "-v",
        "--verison",
        help="Install specific version",
        dest="version",
        action="store",
    )
    update_parser.add_argument(
        "--exit-on-fail",
        help="If any step fails, stop the updater",
        dest="fail",
        action="store_true",
    )
    update_steps_group = update_parser.add_argument_group(
        "steps", "update steps you want to run (if none are selected all will be run)",
    )
    update_steps = {
        "pip": "install the newest version of Cherrydoor via pip",
        "config": "update your config file",
        "database": "Update database schema and settings",
    }
    for (step, description) in update_steps.items():
        update_steps_group.add_argument(
            f"--{step}",
            dest="update_steps",
            action="append_const",
            const=step,
            help=description,
        )
        update_steps_group.add_argument(
            f"--no-{step}",
            dest="update_steps_excluded",
            action="append_const",
            const=step,
            help=f"don't {description}",
        )

    start_parser = subparsers.add_parser(
        "start",
        help="Explicitly start the server (this action is preformed if no other argument is passed too)",
    )
    add_args(parser)
    add_args(start_parser)
    args = parser.parse_args()
    config, _ = load_config(args)
    log_level = getattr(logging, config.get("log_level", "WARN").upper())
    if not isinstance(log_level, int):
        log_level = logging.WARN
        logging.warn(
            "Invalid log level %s - defaulting to WARN",
            config.get("log_level", "WARN").upper(),
        )
    logging.basicConfig(
        level=log_level, format="%(asctime)s:%(name)s:%(levelname)s: %(message)s",
    )
    if args.subcommand == "install":
        from cherrydoor.cli.install import install

        install(args)
    if args.subcommand == "update":
        from cherrydoor.cli.update import update

        update(args)
    # if start argument was passed or no arguments were used, start the server
    if args.subcommand in ["start", None]:
        from cherrydoor.app import setup_app
        from cherrydoor.interface.serial import Serial

        try:
            import uvloop

            uvloop.install()
        except ModuleNotFoundError:
            pass
        loop = asyncio.get_event_loop()
        app = setup_app(loop, config)
        interface = Serial(app["db"], loop)
        app["serial"] = interface
        app.on_startup.append(interface.aiohttp_startup)
        app.on_cleanup.append(interface.cleanup)

        web.run_app(
            app,
            host=config.get("host", "127.0.0.1"),
            port=config.get("port", 5000),
            path=config.get("path", None),
        )


if __name__ == "__main__":
    cherrydoor()
