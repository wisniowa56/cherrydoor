"""
Serial communication and card authentication
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import asyncio
import logging
import sys
from datetime import datetime
from math import ceil
from time import sleep

import aioserial
from motor import motor_asyncio as motor

try:
    import RPi.GPIO as GPIO

    gpio_enabled = True
    GPIO.setmode(GPIO.BCM)
except ModuleNotFoundError:
    gpio_enabled = False


def get_config():
    from cherrydoor.config import load_config

    config, _ = load_config()
    return config


class Serial:
    def __init__(self, motor=None, loop=None, config=get_config()):
        self.config = config
        self.encoding = self.config.get("interface", {}).get("encoding", "utf-8")
        self.manual_auth = False
        self.is_break = False
        self.command_funcions = {"CARD": self.card, "EXIT": sys.exit, "PONG": self.pong}
        self.break_times = []
        self.delay = 0
        self.loop = loop
        self.card_event = asyncio.Event()
        self.last_uid = ""
        self.logger = logging.getLogger("SERIAL")
        self.db = motor
        self.settings_change_stream = None
        self.door_open = False
        self.ping_counter = 0
        if gpio_enabled:
            self.reset_pin = config.get("reset_pin", 27)
            GPIO.setup(self.reset_pin, GPIO.OUT)

    def start(self, run=False):
        try:
            if self.loop == None:
                self.loop = asyncio.get_event_loop()
            if self.db == None:
                self.db = motor.AsyncIOMotorClient(
                    f"mongodb://{self.config.get('mongo', {}).get('url', 'localhost:27017')}/{self.config.get('mongo', {}).get('name', 'cherrydoor')}",
                    username=self.config.get("mongo", {}).get("username", None),
                    password=self.config.get("mongo", {}).get("password", None),
                    io_loop=self.loop,
                )[self.config.get("mongo", {}).get("name", "cherrydoor")]
            self.serial_init(self.config)
            self.loop.create_task(self.commands())
            self.loop.create_task(self.settings_listener())
            self.loop.create_task(self.breaks())
            self.logger.info(
                f"Listening on {self.config.get('interface', {}).get('port', '/dev/serial0')}"
            )
            if run:
                self.loop.run_forever()
            else:
                return self.loop
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt")
            pass
        finally:
            self.cleanup()

    async def aiohttp_startup(self, app):
        app["create_aiohttp_tasks"] = asyncio.create_task(
            self.create_aiohttp_tasks(app)
        )

    async def create_aiohttp_tasks(self, app):
        """
        Create tasks that will be ran constantly after app has started
        """
        await self.async_serial_init()
        app["serial_listener"] = asyncio.create_task(self.commands())
        app["settings_listener"] = asyncio.create_task(self.settings_listener())
        app["breaks_listener"] = asyncio.create_task(self.breaks())
        app["serial_ping"] = asyncio.create_task(self.ping())
        self.logger.info(
            f"Listening on {self.config.get('interface', {}).get('port', '/dev/serial0')}"
        )

    async def cleanup(self, app=None):
        """
        Clean up change streams and serial after app is closed
        """
        if self.settings_change_stream != None:
            await self.settings_change_stream.close()
        await self.serial.close()
        if gpio_enabled:
            GPIO.cleanup()

    def serial_init(self):
        """
        Synchronous function for initializing serial connection - deprecated as of 0.7
        """
        try:
            self.serial = aioserial.AioSerial(
                loop=self.loop,
                port=self.config.get("interface", {}).get("port", "/dev/serial0"),
                baudrate=self.config.get("interface", {}).get("baudrate", 115200),
            )
        except aioserial.serialutil.SerialException as e:
            self.logger.debug(
                "unable to connect to serial, trying again in 2 seconds. Exception: %s",
                str(e),
            )
            sleep(2)
            self.serial_init()

    async def reset(self):
        if gpio_enabled:
            GPIO.output(self.reset_pin, GPIO.LOW)
            await asyncio.sleep(1)
            GPIO.output(self.reset_pin, GPIO.HIGH)

    async def async_serial_init(self, n=1):
        """
        Asynchronous function for initializing serial connection
        """
        try:
            self.serial = aioserial.AioSerial(
                loop=self.loop,
                port=self.config.get("interface", {}).get("port", "/dev/serial0"),
                baudrate=self.config.get("interface", {}).get("baudrate", 115200),
            )
        except aioserial.serialutil.SerialException as e:
            if n <= 20:
                self.logger.info(
                    "unable to connect to serial, trying again in 2 seconds. Exception: %s",
                    str(e),
                )
            elif n == 21:
                self.logger.warning(
                    "unable to connect to serial for more than 40 seconds, logging for this issue stopped until the attempts to connect are successful. Exception: %s",
                    str(e),
                )
            await asyncio.sleep(1 + (n * (n < 25) or 24))
            await self.async_serial_init(n + 1)

    async def commands(self):
        """
        Process commands by listening on serial connection
        """
        while True:
            self.card_event.clear()
            try:
                line = await self.serial.readline_async()
            except aioserial.serialutil.SerialException as e:
                self.logger.exception(
                    "disconnected from serial while trying to read. Exception: %s",
                    str(e),
                )
                await self.async_serial_init()
                continue
            command = line.decode("utf-8", errors="ignore").rstrip().split(" ")
            self.loop.create_task(self.log_command(command))
            if len(command) < 2:
                continue
            process = self.command_funcions.get(command[0], None)
            if process != None:
                await process(command[1])
            await asyncio.sleep(0.5)

    async def card(self, block0):
        self.logger.debug("processing a card")
        uid = self.extract_uid(block0)
        if await self.auth_required():
            result = await self.authenticate(uid)
            auth_mode = "UID"
        else:
            result = block0[-2:] == self.config.get("manufacturer-code", "18")
            auth_mode = "Manufacturer code"
            if result == False:
                self.logger.debug(
                    "manufacturer code doesn't match - card: %s, expected %s",
                    block0[-2:],
                    self.config.get("manufacturer-code", "18"),
                )
                result = await self.authenticate(uid)
                auth_mode = "UID" if result else auth_mode
        if self.delay:
            await asyncio.sleep(self.delay)
        await self.writeline(f"AUTH {int(result)}")
        self.loop.create_task(self.log_entry(block0, auth_mode, result))
        self.logger.debug(
            f"Authentication {'successful' if result else 'unsuccessful'}"
        )
        self.last_uid = uid
        self.card_event.set()

    async def authenticate(self, card):
        result = await self.db.users.count_documents(
            {"permissions": {"$in": ["admin", "enter"]}, "cards": str(card)}
        )
        return result > 0

    async def auth_required(self):
        auth = await self.db.settings.find_one(
            {"setting": "require_auth"}, {"_id": 0, "manual": 1, "value": 1}
        )
        try:
            self.manual_auth = auth.get("manual", False)
        except AttributeError:
            return not self.is_break
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
                self.logger.debug("break time: %s", self.is_break)
                await self.writeline(f"NTFY {3 if self.is_break else 4}")

    async def open(self, open: bool) -> None:
        """
        set status of the door (open/close)
        """
        if not isinstance(open, bool):
            open = open.lower() == "open"
        await self.writeline(f"DOOR {int(open)}")

    async def writeline(self, text):
        try:
            await self.serial.write_async(f"{text}\n".encode(self.encoding))
            self.serial.flush()
        except (aioserial.serialutil.SerialException, AttributeError) as e:
            self.logger.exception("Serial exception while trying to write. %s", str(e))
            await self.async_serial_init()

    async def log_entry(self, block0: str, auth_mode: str, success: bool):
        await self.db.logs.insert_one(
            {
                "timestamp": datetime.now(),
                "card": self.extract_uid(block0),
                "manufacturer_code": block0[-2:],
                "auth_mode": auth_mode,
                "success": success,
            }
        )

        await asyncio.sleep(0.1)
        self.card_event.clear()

    async def log_command(self, command):
        await self.db.terminal.insert_one(
            {
                "command": command[0],
                "arguments": command[1:],
                "source": "serial",
                "timestamp": datetime.now(),
            }
        )

    async def ping(self):
        """
        Test connection to arduino every 0.5 second
        TODO #54 create and use a new status command instead of a ping/pong
        """
        while True:
            if self.ping_counter > 1 and self.ping_counter < 10:
                self.logger.debug("Unsuccessful ping")
            elif self.ping_counter >= 10 and self.ping_counter < 20:
                self.logger.error(
                    "Pings were unsuccessful for more than 10 seconds - there is most likely an error on the other side of the serial connection"
                )
            elif self.ping_counter == 20:
                self.logger.error(
                    "Pings were unsuccessful for a long time - stopping logging"
                )
            await self.writeline("PING")
            self.ping_counter += 1
            await asyncio.sleep(1)

    async def pong(self, status=0):
        """
        Acknowledge ping return and use the argument to set current door status
        TODO create and use a new status command instead of a ping/pong
        """
        self.ping_counter = 0
        self.door_open = int(status) > 0

    def extract_uid(self, block0):
        if isinstance(block0, str):
            try:
                if len(block0) % 2 != 0:
                    self.logger.debug(
                        "padding block0 with 0 before manufacturere code. Contents before modification: %s",
                        block0,
                    )
                    block0 = block0[:-2] + "0" + block0[-2:]
                block0 = bytearray.fromhex(block0)
            except ValueError as e:
                self.logger.debug(
                    "Invalid block0 string - %s. block0: %s", str(e), block0
                )
                return block0
        elif not isinstance(block0, bytearray):
            self.logger.error(
                "%s is not a valid type for block0 (valid types are string and bytearray)",
                type(block0).__name__,
            )
            return None
        uid = bytearray()
        uid_len = 4 + 3 * (block0[0] == 0x88) * (1 + (block0[5] == 0x88))
        for i, byte in enumerate(block0):
            if (
                i == 4
                or (uid_len in [7, 10] and i == 0)
                or (uid_len == 10 and i in [5, 9, 14])
            ):
                if byte != 0x88:
                    bcc = block0[i - 1] ^ block0[i - 2] ^ block0[i - 3] ^ block0[i - 4]
                    if byte != bcc:
                        self.logger.error(
                            "Invalid bcc in uid %s, recieved bcc: %s, expected bcc: %s",
                            uid,
                            byte,
                            bcc,
                        )
                        self.logger.debug(
                            "Whole block0 invalid bcc was found in: %s, position: %s",
                            block0,
                            i,
                        )
                        return None
                    elif len(uid) >= uid_len:
                        break
                continue
            uid.append(byte)
            if len(uid) > uid_len:
                break
        return uid.hex()


if __name__ == "__main__":
    serial = Serial()
    serial.start()
