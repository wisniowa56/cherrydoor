from json import load
from pathlib import Path

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.6.b0"
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
