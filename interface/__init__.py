from json import load
from pymongo import MongoClient

with open("config.json", "r", encoding="utf-8") as f:  # load configuration file
    config = load(f)  # convert confuguration to a dictionary using json.load()

try:
    # set up PyMongo using credentials from config.json
    mongo = MongoClient(
        f"mongodb://\
{config['mongo']['username']}:\
{config['mongo']['password']}@\
{config['mongo']['url']}/\
{config['mongo']['name']}"
    )[config["mongo"]["name"]]
except KeyError:
    # if username or password aren't defined in config, don't use them at all
    mongo = MongoClient(f"mongodb://{config['mongo']['url']}")[config["mongo"]["name"]]

try:
    if config["interface"]["type"].lower() == "serial":
        import serial

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
