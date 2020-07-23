from json import load
from pymongo import MongoClient
from pathlib import Path

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.5.dev"
__status__ = "Prototype"

default_routes = [
    "config.json",
    "/var/cherrydoor/config.json",
    f"{Path.home()}/.config/cherrydoor/config.json",
]
for route in default_routes:
    try:
        # load configuration file from one of the default routes
        with open(route, "r", encoding="utf-8") as f:
            # convert confuguration to a dictionary using json.load()
            config = load(f)
            break
    except FileNotFoundError:
        # ignore if config wasn't found
        pass
if config == None:
    raise FileNotFoundError("No config.json found")
try:
    if config["mongo"]:

        try:
            # set up PyMongo using credentials from config.json
            db = MongoClient(
                f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}",
                username=config["mongo"]["username"],
                password=config["mongo"]["password"],
            ).cherrydoor
        except KeyError:
            # if username or password aren't defined in config, don't use them at all
            db = MongoClient(
                f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}"
            ).cherrydoor
        try:
            db.client.server_info()
        except Exception as e:
            print(
                f"Connection to MongoDB failed. Are you sure it's installed and correctly configured? Error: {e}"
            )
except KeyError:
    print("No supported database present in config.json")

try:
    if config["interface"]["type"].lower() == "serial":
        import serial

        connectionException = serial.serialutil.SerialException
        interface = serial.Serial()
        try:
            interface.baudrate = int(config["interface"]["baudrate"])
        except (KeyError, AttributeError):
            # default to 115200 if no baudrate is found in config
            interface.baudrate = 115200
        try:
            interface.port = config["interface"]["port"]
        except (KeyError, AttributeError):
            # default to /dev/serial0 (default for RaspberryPi UART)
            interface.port = "/dev/serial0"
        try:

            encoding = config["interface"]["encoding"]
        except KeyError:
            # default to utf-8 if no encoding information found in config
            encoding = "utf-8"

        def read():
            message = interface.readline().decode(encoding)
            return message

        def write(message):
            interface.write(f"{message}\n".encode(encoding))
            interface.flush()

    else:
        raise KeyError("Unknown interface type")
except (KeyError, AttributeError):
    # default to serial if no compatible interface if found in config file, or interface is not a string
    import serial

    connectionException = serial.serialutil.SerialException
    interface = serial.Serial()
    try:
        interface.baudrate = int(config["interface"]["baudrate"])
    except (KeyError, AttributeError):
        # default to 115200 if no baudrate is found in config
        interface.baudrate = 115200
    try:
        interface.port = config["interface"]["port"]
    except (KeyError, AttributeError):
        # default to /dev/serial0 (default for RaspberryPi UART)
        interface.port = "/dev/serial0"
    try:
        encoding = config["interface"]["encoding"]
    except KeyError:
        # default to utf-8 if no encoding information found in config
        encoding = "utf-8"

    def read():
        message = interface.readline().decode(encoding)
        return message

    def write(message):
        interface.write(f"{message}\n".encode(encoding))
        interface.flush()
