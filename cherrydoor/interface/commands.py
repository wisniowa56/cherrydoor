import datetime as dt
from time import sleep
from datetimerange import DateTimeRange
from cherrydoor.interface import read, write, db, config, interface, connectionException

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.4"
__status__ = "Prototype"


class Commands:
    def __init__(self):
        self.commandFunctions = {"CARD": self.card}
        try:
            self.require_auth = bool(
                db.settings.find_one({"setting": "require_auth"})["value"]
            )
            write(f"NTFY {4 if self.require_auth else 3}")
        except (KeyError, TypeError):
            self.require_auth = True

    def start(self):
        # message template - a two element list (command and argument)
        message = ["", ""]
        try:
            with interface:
                # continuously read the interface until EXIT is sent
                while message == [] or message[0] != "EXIT":
                    message = read().upper().split()
                    # after a newline, do the specidied command
                    try:
                        self.commandFunctions[message[0]](message[1])
                    except (KeyError, IndexError):
                        pass
        except connectionException:
            sleep(10)
            self.start()

    def card(self, block0):
        try:
            # check if authentication with UID is required, or manufacturer code is fine
            self.require_auth = self.check_auth()
            # send a contol signal for LEDs
            write(f"NTFY {4 if self.require_auth else 3}")
        except:
            # default to requiring authentication
            self.require_auth = True
        if self.require_auth:
            # check if card is associated with an user
            auth = bool(db.users.count_documents({"cards": block0[:10]}))
        else:
            try:
                # if authentication is not required check manufacturer code - 2 last digits of block0
                auth = block0[-2:] == config["manufacturer-code"]
            except KeyError:
                auth = False
        # add attempt to logs
        db.logs.insert(
            {
                "timestamp": dt.datetime.now(),
                "card": block0[:10],
                "manufacturer_code": block0[-2:],
                "auth_mode": "UID" if self.require_auth else "Manufacturer code",
                "success": auth,
            }
        )
        # send the authentication result over the interface
        write(f"AUTH {1 if auth else 0}")

    def check_auth(self):
        time = dt.datetime.now().time()
        try:
            # get the list of break times from database
            breaks = list(db.settings.find_one({"setting": "break_times"})["value"])
            # get the current setting
            require_auth = db.settings.find_one({"setting": "require_auth"})
            # if the current setting was set manually - don't check the time
            if bool(require_auth["manual"]):
                return bool(require_auth["value"])
            for item in breaks:
                # if current time is in one of the time ranges, return False, so auth is not required
                if time in DateTimeRange(item[0].time(), item[1].time()):
                    return False
            return True

        except (KeyError, TypeError):
            # default to requiring auth
            return True
