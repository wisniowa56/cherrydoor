"""
Load configuration
"""

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.8.b0"
__status__ = "Prototype"

import argparse
from uuid import uuid4

import confuse


# add otpional type, because confuse doesn't have it yet
def optional(type, default=None):
    template = confuse.as_template(type)
    template.default = default
    return template


template = {
    "version": optional(confuse.OneOf([str, int]), __version__),
    "host": str,
    "port": optional(int),
    "path": optional(confuse.Filename()),
    "mongo": {
        "url": str,
        "name": str,
        "username": optional(str),
        "password": optional(str),
    },
    "interface": {
        "port": confuse.OneOf([confuse.String(pattern="COM\d+$"), confuse.Filename()]),
        "baudrate": int,
        "encoding": optional(str, "utf-8"),
    },
    "manufacturer_code": confuse.String(pattern="^[a-fA-F0-9]{2}$"),
    "secret_key": optional(str),
    "max_session_age": confuse.OneOf([int, None]),
    "https": optional(bool, False),
    "sentry_dsn": optional(str),
    "sentry_csp_url": optional(str),
    "log_level": optional(str),
}

config = confuse.LazyConfig("cherrydoor", __name__)


def add_args(parser):
    args_template = {
        "host": {
            "type": str,
            "help": "host address used for serving the website",
            "dest": "host",
        },
        "port": {
            "type": int,
            "help": "port on which the website will be served",
            "dest": "port",
        },
        "mongo-url": {
            "type": str,
            "help": "url for mongodb instance",
            "dest": "mongo.url",
        },
        "mongo-name": {
            "type": str,
            "help": "name of the database",
            "dest": "mongo.name",
        },
        "mongo-username": {
            "type": str,
            "help": "name of a user with at least readwrite permission on the database",
            "dest": "mongo.username",
        },
        "mongo-password": {
            "type": str,
            "help": "password of a user with at least readwrite permission on the database",
            "dest": "mongo.password",
        },
        "serial-port": {
            "type": str,
            "help": "port arduino is available on",
            "dest": "interface.port",
        },
        "serial-baudrate": {
            "type": str,
            "help": "baudrate of the arduino",
            "dest": "interface.baudrate",
        },
        "serial-encoding": {
            "type": str,
            "help": "encoding used by arduino (default utf-8 is probably the best idea)",
            "dest": "interface.encoding",
        },
        "manufacturer-code": {
            "type": str,
            "help": "Last two digits of block 0 of cards you want to allow during breaks",
            "dest": "manufacturer_code",
        },
        "secret-key": {
            "type": str,
            "help": "secret used for csrf and other stuff. Ideally a totally random value",
            "dest": "secret_key",
        },
        "max-session-age": {
            "type": int,
            "help": "maximum amount of time a session can be active",
            "dest": "max_session_age",
        },
        "https": {
            "type": bool,
            "help": "whether the app is using https (modifies some security headers)",
            "dest": "https",
        },
        "log-level": {
            "type": str,
            "help": "Log level shown (defaults to WARN)",
            "dest": "log_level",
        },
    }
    config_group = parser.add_argument_group(
        title="config", description="configuration options"
    )
    config_group.set_defaults(env=True, config=None)
    config_group.add_argument(
        "--no-env",
        help="don't use environmental variables for cofiguration",
        dest="env",
        action="store_false",
    )
    config_group.add_argument(
        "--config",
        help="Specify a config file overriding default location",
        type=argparse.FileType("r"),
        dest="config",
    )
    for (setting, attributes) in args_template.items():
        config_group.add_argument(
            f"--{setting}",
            help=attributes.get("help", ""),
            type=attributes.get("type", str),
            dest=attributes.get("dest", None),
        )

    return parser


def load_config(args=None):
    if args != None:
        if args.config != None:
            config.set_file(args.config.name)
        if args.env:
            config.add(load_env())
        config.set_args(args, dots=True)
    valid_config = config.get(template)
    if valid_config.get("secret_key", None) == None:
        valid_config["secret_key"] = str(uuid4())
    return valid_config, config


def load_env():
    from os import environ

    return confuse.ConfigSource.of(dict(environ))
