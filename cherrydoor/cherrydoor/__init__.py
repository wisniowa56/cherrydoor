#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the server"""
from multiprocessing import Process
import argparse
import sys
import os
import json
from subprocess import call
from argon2 import PasswordHasher
from pymongo import MongoClient


def cherrydoor():
    parser = argparse.ArgumentParser(description="Cherrydoor management")
    subparsers = parser.add_subparsers(dest="subcommand")
    install_parser = subparsers.add_parser(
        "install", help="Install some possible requirements"
    )
    start_parser = subparsers.add_parser(
        "start",
        help="Explicitly start the server (this action is preformed if no other argument is passed too)",
    )

    args = parser.parse_args()
    if args.subcommand == "install":
        from getpass import getpass

        if sys.platform == "linux":
            # install database and some other things if they're not installed
            try:
                call("cherrydoor-install")
            except (PermissionError, FileNotFoundError):
                pass
            # generate a configuration based on default config
            if not os.path.exists("/var/cherrydoor/config.json"):
                config = {
                    "__comment__": "This is a backup default config for setuptools installation - it shouldn't be used if installed from GitHub",
                    "host": "127.0.0.1",
                    "port": 5000,
                    "mongo": {
                        "url": "localhost:27017",
                        "name": "cherrydoor2",
                        "username": "cherrydoor",
                        "password": "test",
                    },
                    "login-translation": {
                        "username": "Nazwa użytkownika",
                        "password": "Hasło",
                        "remember-me": "Pamiętaj mnie",
                        "log-in": "Zaloguj się",
                        "message": "Musisz się zalogować by uzyskać dostęp do tej strony",
                    },
                    "secret-key": "\\xd7w7\\x04\\r\\xfc/q\\x1a\\x9b&",
                    "https": {
                        "enabled": False,
                        "hsts-enabled": False,
                        "hsts-preload": False,
                    },
                    "interface": {
                        "type": "serial",
                        "baudrate": 115200,
                        "port": "/dev/serial0",
                        "encoding": "utf-8",
                    },
                    "manufacturer-code": "18",
                }
            else:
                with open("/var/cherrydoor/config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            # create a random secret key
            config["secret-key"] = os.urandom(24).hex()
            # let user choose a password for the database
            config["mongo"]["password"] = getpass("Wprowadź hasło do bazy danych: ")
            try:
                # files configuration
                if not os.path.exists("/var/cherrydoor"):
                    os.makedirs("/var/cherrydoor")
                with open("/var/cherrydoor/config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f)
                with open("/etc/systemd/system/cherrydoor.service", "w") as f:
                    f.write(
                        f"""\
[Unit]
Description=Cherrydoor Service
After=network.target
[Service]
ExecStart={os.path.realpath(__file__)} start
Environment=PYTHONUNBUFFERED=1
Restart=always
Type=simple
User=ubuntu
[Install]
WantedBy=multi-user.target
"""
                    )
                    call(
                        "sudo systemctl enable cherrydoor && sudo systemctl daemon-reload"
                    )
            except (IOError, PermissionError):
                print(
                    "Potrzebujesz do tego uprawnień roota. Spróbuj uruchomić skrypt z użyciem 'sudo'",
                    file=sys.stderr,
                )
                sys.exit(1)

            hasher = PasswordHasher(
                time_cost=4,
                memory_cost=65536,
                parallelism=8,
                hash_len=16,
                salt_len=16,
                encoding="utf-8",
            )
            db = MongoClient(
                f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}"
            ).db

            db.command(
                "createUser",
                config["mongo"]["username"],
                pwd=config["mongo"]["password"],
                roles=[
                    {"role": "readWrite", "db": config["mongo"]["name"]},
                    {"role": "clusterMonitor", "db": "admin"},
                ],
            )
            db.create_collection("users")
            db.create_collection("logs")
            db.create_collection("settings")
            if input(
                "Czy chcesz stworzć nowego użytkownika-administratora? [y/n]"
            ).lower() in ["y", "yes", "tak", "t"]:
                username = input("Wprowadź nazwę użytkownika: ")
                password = hasher.hash(getpass("Hasło: "))
                db.users.insert(
                    {"username": username, "password": password, "cards": []}
                )
            print(
                "Instalacja skończona! Plik konfiguracyjny znajduje się w folderze /var/cherrydoor/"
            )
        else:
            print("Ten system operacyjny nie jest obecnie obsługiwany")

        sys.exit()
    # if start argument was passed or no arguments were used, start the server
    if args.subcommand == "start" or not len(sys.argv) > 1:
        from cherrydoor.server import app, socket, config
        from cherrydoor.interface.commands import Commands

        interface = Commands()
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

        def exit():
            interface_run.terminate()
            server.terminate()

        import atexit

        atexit.register(exit)
        interface_run.start()
        server.run()


if __name__ == "__main__":
    cherrydoor()
