#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the server"""
from multiprocessing import Process
import argparse
import sys
import os
import json
from argon2 import PasswordHasher
from pymongo import MongoClient


def cherrydoor():
    parser = argparse.ArgumentParser(
        prog="cherrydoor", description="Cherrydoor management"
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

    start_parser = subparsers.add_parser(
        "start",
        help="Explicitly start the server (this action is preformed if no other argument is passed too)",
    )

    args = parser.parse_args()
    if args.subcommand == "install":
        from cherrydoor.cli.install import install

        install(args)

    # if start argument was passed or no arguments were used, start the server
    if args.subcommand == "start" or not len(sys.argv) > 1:
        from cherrydoor.server import app, socket, config
        from cherrydoor.interface.serial import Serial

        interface = Serial()
        interface_run = Process(target=interface.start)
        server = Process(
            target=socket.run,
            kwargs={
                "app": app,
                "log_output": True,
                "host": config["host"],
                "port": config["port"],
            },
        )

        def exit(interface_run, server):
            print("Closing server and serial connections")
            interface_run.terminate()
            # server.terminate()
            sys.exit()

        import atexit

        atexit.register(exit, interface_run, server)
        interface_run.start()
        server.run()


if __name__ == "__main__":
    cherrydoor()
