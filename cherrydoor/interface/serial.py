import asyncio
from datetime import datetime
from math import ceil
from time import sleep
import sys

from motor import motor_asyncio as motor
import aioserial

from cherrydoor.interface import config

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.0"
__status__ = "Prototype"


class Serial:
    def __init__(self):
        self.encoding = config.get("interface", {}).get("encoding", "utf-8")
        self.manual_auth = False
        self.is_break = False
        self.command_funcions = {"CARD": self.card, "EXIT": sys.exit}
        self.terminal_change_stream = None
        self.break_times = []
        self.delay = 0

    def start(self):
        try:
            self.loop = asyncio.get_event_loop()
            self.db = motor.AsyncIOMotorClient(
                f"mongodb://{config.get('mongo', {}).get('url', 'localhost:27017')}/{config.get('mongo', {}).get('name', 'cherrydoor')}",
                username=config.get("mongo", {}).get("username", None),
                password=config.get("mongo", {}).get("password", None),
                io_loop=self.loop,
            )[config.get("mongo", {}).get("name", "cherrydoor")]
            self.serial_init()
            self.loop.create_task(self.commands())
            self.loop.create_task(self.settings_listener())
            self.loop.create_task(self.breaks())
            self.loop.create_task(self.terminal_listener())
            print("Listening on serial interface")
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            if self.terminal_change_stream is not None:
                self.terminal_change_stream.close()
            if self.settings_change_stream is not None:
                self.settings_change_stream.close()

    def serial_init(self):
        try:
            self.serial = aioserial.AioSerial(
                loop=self.loop,
                port=config.get("interface", {}).get("port", "/dev/serial0"),
                baudrate=config.get("interface", {}).get("baudrate", 115200),
            )
        except aioserial.serialutil.SerialException:
            sleep(2)
            self.serial_init()

    async def commands(self):
        while True:
            line = await self.serial.readline_async()
            command = line.decode("utf-8", errors="ignore").rstrip().split(" ")
            self.loop.create_task(self.log_command(command))
            if len(command) < 2:
                continue
            process = self.command_funcions.get(command[0], None)
            if process != None:
                await process(command[1])
            await asyncio.sleep(0.5)

    async def card(self, block0):
        print("processing a card")
        if await self.auth_required():
            result = await self.authenticate(block0[:10])
            auth_mode = "UID"
        else:
            result = block0[-2:] == config.get(
                "manufacturer-code", "18"
            ) or await self.authenticate(block0[:10])
            auth_mode = "Manufacturer code"
        if self.delay:
            await asyncio.sleep(self.delay)
        await self.writeline(f"AUTH {1 if result else 0}")
        self.loop.create_task(self.log_entry(block0, auth_mode, result))
        print(f"Authentication {'successful' if result else 'unsuccessful'}")

    async def authenticate(self, card):
        result = await self.db.users.count_documents(
            {"cards": str(card)}
            # prepare for implementation of a privilege system:
            # {"cards": str(card), "privileges": {"$in": ["enter", "admin"]}}
        )
        return result > 0

    async def auth_required(self):
        auth = await self.db.settings.find_one(
            {"setting": "require_auth"}, {"_id": 0, "manual": 1, "value": 1}
        )
        try:
            self.manual_auth = auth.get("manual", False)
        except AttributeError:
            self.manual_auth = False
        if self.manual_auth:
            return auth.get("value", True)
        return not self.is_break

    async def settings_listener(self):
        break_documents = await self.db.settings.find_one({"setting": "break_times"})
        self.break_times = break_documents.get("value", [])
        async with self.db.settings.watch(
            pipeline=[
                {
                    "$match": {
                        "fullDocument.setting": {"$in": ["break_times", "delay"]},
                        "operationType": {"$in": ["insert", "update", "replace"]},
                    }
                },
                {
                    "$project": {
                        "value": "$fullDocument.value",
                        "setting": "$fullDocument.setting",
                    }
                },
            ],
            full_document="updateLookup",
        ) as self.settings_change_stream:
            async for change in self.settings_change_stream:
                setting = change.get("setting", "")
                if setting == "break_times":
                    self.break_times = change.get("value", [])
                    print(f"new break times: {self.break_times}")
                elif setting == "delay":
                    self.delay = change.get("value", 0)
                    print(f"new response delay: {self.delay}s")

    async def breaks(self):
        while True:
            now = datetime.now()
            next_time = datetime.fromtimestamp(ceil(now.timestamp()))
            delta = next_time - now
            await asyncio.sleep(delta.total_seconds())
            time = next_time.replace(year=2020, month=2, day=2)
            previous = self.is_break
            for break_time in self.break_times:
                self.is_break = time > break_time.get(
                    "from", datetime.max
                ) and time < break_time.get("to", datetime.min)
            if previous != self.is_break and not self.manual_auth:
                await self.writeline(f"NTFY {4 if self.is_break else 3}")

    async def writeline(self, text):
        await self.serial.write_async(f"{text}\n".encode(self.encoding))
        self.serial.flush()

    async def log_entry(self, block0, auth_mode, success):
        await self.db.logs.insert_one(
            {
                "timestamp": datetime.now(),
                "card": block0[:10],
                "manufacturer_code": block0[-2:],
                "auth_mode": auth_mode,
                "success": success,
            }
        )

    async def log_command(self, command):
        await self.db.terminal.insert_one(
            {
                "command": command[0],
                "arguments": command[1:],
                "source": "serial",
                "timestamp": datetime.now(),
            }
        )

    async def terminal_listener(self):
        async with self.db.terminal.watch(
            pipeline=[
                {
                    "$match": {
                        "fullDocument.source": {"$ne": "serial"},
                        "operationType": "insert",
                    }
                },
            ],
            full_document="updateLookup",
        ) as self.terminal_change_stream:
            async for change in self.terminal_change_stream:
                document = change.get("fullDocument", {})
                command = " ".join(
                    [change.get("command", ""), *change.get("arguments", [])]
                )
                await self.writeline(command)


if __name__ == "__main__":
    serial = Serial()
    serial.start()
