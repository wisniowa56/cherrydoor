import datetime as dt

from interface import read, write, mongo, config, interface


class Commands:
    def __init__(self, pipe):
        self.commands = {
            "CARD": self.card,
        }
        self.pipe = pipe
        if self.pipe.poll():
            self.require_auth = self.pipe.recv()
            write(f"NTFY {4 if self.require_auth else 3}")
        else:
            self.require_auth = True

    def start(self):
        message = ["", ""]
        with interface:
            while message == [] or message[0] != "EXIT":
                message = read().upper().split()
                try:
                    self.commands[message[0]](message[1])
                except (KeyError, IndexError):
                    pass
                except BrokenPipeError:
                    break

    def card(self, block0):
        if self.pipe.poll():
            self.require_auth = self.pipe.recv()
            write(f"NTFY {4 if self.require_auth else 3}")
        if self.require_auth:
            auth = bool(mongo.users.count_documents({"cards": block0[:10]}))
        else:
            try:
                auth = block0[-2:] == config["manufacturer-code"]
            except KeyError:
                auth = False
        mongo.logs.insert(
            {
                "timestamp": dt.datetime.now(),
                "card": block0[:10],
                "manufacturer_code": block0[-2:],
                "auth_mode": "UID" if self.require_auth else "Manufacturer code",
                "success": auth,
            }
        )
        write(f"AUTH {1 if auth else 0}")
