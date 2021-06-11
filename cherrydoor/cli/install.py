"""
Install the app for the first time
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"
import json
import os
import sys
from getpass import getpass
from pathlib import Path
from subprocess import call  # nosec

from argon2 import PasswordHasher
from pymongo import MongoClient
from pymongo.errors import OperationFailure


def step_enabled(step, args):
    return step not in args.install_steps_excluded and (
        args.install_steps == [] or step in args.install_steps
    )


def install(args):
    if sys.platform == "linux" or 1 == 1:

        if step_enabled("dependencies", args):
            # install MongoDB and some other things if they're not installed
            try:
                call(["cherrydoor-install"], shell=False)  # nosec
            except (PermissionError, FileNotFoundError):
                print("unable to install dependencies")
                if args.fail:
                    sys.exit(1)
        # generate a configuration based on default config
        if (
            not os.path.exists(f"{Path.home()}/.config/cherrydoor/config.json")
            or "config" in args.install_steps
        ):
            config = {
                "__comment__": "This is a default config for setuptools installation - it shouldn't be used if installed from GitHub",
                "host": "127.0.0.1",
                "port": 5000,
                "mongo": {
                    "url": "localhost:27017",
                    "name": "cherrydoor",
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
            with open(
                f"{Path.home()}/.config/cherrydoor/config.json", "r", encoding="utf-8"
            ) as f:
                config = json.load(f)
        if step_enabled("config", args):
            # create a random secret key
            config["secret-key"] = os.urandom(24).hex()
            # let user choose a password for the database
            if step_enabled("database", args):
                config["mongo"]["password"] = getpass("Wprowadź hasło do bazy danych: ")
            try:
                # files configuration
                if not os.path.exists(f"${Path.home()}"):
                    os.makedirs(f"{Path.home()}/.config/cherrydoor")
                with open(
                    f"{Path.home()}/.config/cherrydoor/config.json",
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
            except (IOError, PermissionError):
                print(
                    f"Nie udało się stworzyć plików w {Path.home()}/.config/cherrydoor. Spróbuj stworzyć ten folder manualnie i nadać mu właściwe uprawnienia",
                    file=sys.stderr,
                )
                if args.fail:
                    sys.exit(1)
        if step_enabled("service", args):
            service_config = f"""\
[Unit]
Description=Cherrydoor Service
After=network.target
[Service]
ExecStart={os.path.realpath(__file__).replace("install.py", "__init__.py")} start
Environment=PYTHONUNBUFFERED=1
Restart=always
Type=simple
User=ubuntu
[Install]
WantedBy=multi-user.target
"""
            try:
                if not os.path.exists(f"{Path.home()}/.config/systemd/user"):
                    os.makedirs(f"{Path.home()}/.config/systemd/user")
                with open(
                    f"{Path.home()}/.config/systemd/user/cherrydoor.service", "w"
                ) as f:
                    f.write(service_config)
                    print(
                        f"Plik konfiguracyjny znajduje się w folderze {Path.home()}/.config/cherrydoor"
                    )
            except (IOError, PermissionError):
                print(
                    f"Nie udało się stworzyć pliku usługi pod {Path.home()}/.config/systemd/user/cherrydoor.service - spróbuj uruchomić skrypt z właściwymi uprawnieniami lub stworzyć ten plik manualnie. Zawartość:",
                    file=sys.stderr,
                )
                print(service_config, file=sys.stderr)
                if args.fail:
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
        )[config["mongo"]["name"]]
        if step_enabled("database", args):
            try:
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
                db.create_collection(
                    "logs", options={"size": 1073742000, "capped": True}
                )
                db.create_collection("settings")
                db.create_collection(
                    "terminal", options={"size": 1048576, "capped": True, "max": 10000}
                )
            except OperationFailure:
                pass
            user_indexes = db.users.index_information()
            if "username_index" not in user_indexes.keys():
                db.users.create_index("username", name="username_index", unique=True)
            if "cards_index" not in user_indexes.keys():
                db.users.create_index("cards", name="cards_index", sparse=True)
        # nosec - it's python3, not 2, Bandit...
        if step_enabled("user", args) and input(
            "Czy chcesz stworzć nowego użytkownika-administratora? [y/n]"
        ).lower() in ["y", "yes", "tak", "t"]:
            # nosec - it's python3, not 2, Bandit...
            username = input("Wprowadź nazwę użytkownika: ")
            password = hasher.hash(getpass("Hasło: "))
            db.users.insert({"username": username, "password": password, "cards": []})
        print("Instalacja skończona!")
        try:
            service_call_args = ["systemctl", "--user", "enable", "cherrydoor"]
            call(service_call_args, shell=False)  # nosec
        except (IOError, PermissionError):
            pass
    else:
        print("Ten system operacyjny nie jest obecnie obsługiwany")

    sys.exit()
