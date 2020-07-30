import datetime as dt
from time import sleep
from datetimerange import DateTimeRange
from cherrydoor.interface import config
from pymongo import MongoClient
from pymongo.errors import OperationFailure
import serial

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.5.2"
__status__ = "Prototype"


class Commands:
    def __init__(self):
        self.commandFunctions = {"CARD": self.card}

    def start(self):
        try:
            if config["mongo"]:
                try:
                    # set up PyMongo using credentials from config.json
                    self.db = MongoClient(
                        f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}",
                        username=config["mongo"]["username"],
                        password=config["mongo"]["password"],
                    ).cherrydoor
                except KeyError:
                    # if username or password aren't defined in config, don't use them at all
                    self.db = MongoClient(
                        f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}"
                    ).cherrydoor
                try:
                    self.db.client.server_info()
                except Exception as e:
                    print(
                        f"Connection to MongoDB failed. Are you sure it's installed and correctly configured? Error: {e}"
                    )
        except KeyError:
            print("No supported database present in config.json")
        self.interface = serial.Serial()
        try:
            self.interface.baudrate = int(config["interface"]["baudrate"])
        except (KeyError, AttributeError):
            # default to 115200 if no baudrate is found in config
            self.interface.baudrate = 115200
        try:
            self.interface.port = config["interface"]["port"]
        except (KeyError, AttributeError):
            # default to /dev/serial0 (default for RaspberryPi UART)
            self.interface.port = "/dev/serial0"
        try:
            self.encoding = config["interface"]["encoding"]
        except KeyError:
            # default to utf-8 if no encoding information found in config
            self.encoding = "utf-8"
        try:
            self.require_auth = bool(
                self.db.settings.find_one({"setting": "require_auth"})["value"]
            )
            with self.interface:
                self.write(f"NTFY {4 if self.require_auth else 3}")
        except (KeyError, TypeError, OperationFailure):
            self.require_auth = True
        self.listen()

    def listen(self):
        # message template - a two element list (command and argument)
        message = ["", ""]
        try:
            with self.interface:
                print("[serial] Listening on serial interface")
                # continuously read the interface until EXIT is sent
                while message == [] or message[0] != "EXIT":
                    message = self.read().upper().split()
                    # after a newline, do the specidied command
                    try:
                        self.commandFunctions[message[0]](message[1])
                        message = []
                    except (KeyError, IndexError):
                        pass
                    if len(message) < 2:
                        message = ["", ""]
        except serial.serialutil.SerialException:
            sleep(10)
            self.listen()

    def card(self, block0):
        print("[serial] processing a card")
        try:
            # check if authentication with UID is required, or manufacturer code is fine
            self.require_auth = self.check_auth()
            # send a contol signal for LEDs
            self.write(f"NTFY {4 if self.require_auth else 3}")
        except:
            # default to requiring authentication
            self.require_auth = True
        if self.require_auth:
            # check if card is associated with an user
            auth = bool(self.db.users.count_documents({"cards": block0[:10]}))
        else:
            try:
                # if authentication is not required check manufacturer code - 2 last digits of block0
                auth = block0[-2:] == config["manufacturer-code"]
            except KeyError:
                auth = False
        # add attempt to logs
        self.db.logs.insert(
            {
                "timestamp": dt.datetime.now(),
                "card": block0[:10],
                "manufacturer_code": block0[-2:],
                "auth_mode": "UID" if self.require_auth else "Manufacturer code",
                "success": auth,
            }
        )
        # send the authentication result over the interface
        self.write(f"AUTH {1 if auth else 0}")
        print(
            "[serial] authentication successful"
            if auth
            else "[serial] unsuccessful authentication attempt"
        )
        return auth

    def check_auth(self):
        time = dt.datetime.now().replace(year=2020, month=2, day=2)
        try:
            # get the list of break times from database
            breaks = self.db.settings.count_documents(
                {
                    "setting": "break_times",
                    "value.from": {"$lte": time},
                    "value.to": {"$gte": time},
                }
            )
            # get the current setting
            require_auth = self.db.settings.find_one({"setting": "require_auth"})
            # if the current setting was set manually - don't check the time
            if require_auth != None and bool(require_auth["manual"]):
                return bool(require_auth["value"])
            return breaks <= 0

        except (KeyError, TypeError):
            # default to requiring auth
            return True

    def write(self, message):
        self.interface.write(f"{message}\n".encode(self.encoding))
        self.interface.flush()

    def read(self):
        message = self.interface.readline().decode(self.encoding)
        return message
