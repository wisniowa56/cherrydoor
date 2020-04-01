from json import load
from pymongo import MongoClient

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.4"
__status__ = "Prototype"

try:
    with open("config.json", "r", encoding="utf-8") as f:  # load configuration file
        config = load(f)  # convert confuguration to a dictionary using json.load()
except FileNotFoundError:
    # load configuration file from `/var/cherrydoor` if it exists
    with open("/var/cherrydoor/config.json", "r", encoding="utf-8") as f:
        # convert confuguration to a dictionary using json.load())
        config = load(f)
try:
    if config["mongo"]:
        from flask_pymongo import PyMongo

        app.config[
            "MONGO_URI"
        ] = f"mongodb://{config['mongo']['url']}/{config['mongo']['name']}"
        try:
            # set up PyMongo using credentials from config.json
            db = PyMongo(
                app,
                username=config["mongo"]["username"],
                password=config["mongo"]["password"],
            ).db
        except KeyError:
            # if username or password aren't defined in config, don't use them at all
            db = PyMongo(app).db
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
