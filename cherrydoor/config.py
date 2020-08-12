import confuse
import argparse

# add otpional type, because confuse doesn't have it yet
def optional(type):
    template = confuse.as_template(type)
    template.default = None
    return template


template = {
    "host": str,
    "port": int,
    "mongo": {
        "url": str,
        "name": str,
        "username": optional(str),
        "password": optional(str),
    },
    "interface": {
        "port": confuse.OneOf([confuse.Filename(), confuse.String(pattern="COM\d+$")]),
        "baudrate": int,
        "encoding": str,
    },
    "manufacturer_code": confuse.String(pattern="^[a-fA-F0-9]{2}$"),
    "secret_key": str,
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
        "manufacturer_code": {
            "type": str,
            "help": "Last two digits of block 0 of cards you want to allow during breaks",
            "dest": "manufacturer_code",
        },
        "secret_key": {
            "type": str,
            "help": "secret used for csrf and other stuff. Ideally a totally random value",
            "dest": "secret_key",
        },
    }
    config_group = parser.add_argument_group(
        title="config", description="configuration options"
    )
    config_group.set_defaults(env=True, config=None)
    cofig_group.add_argument(
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
    for (setting, attributes) in args_template:
        config_group.add_argument(
            f"--{setting}",
            help=attributes.help,
            type=attributes.type,
            dest=attributes.dest,
        )

    return parser


def load_config(args=None):
    if args != None:
        if args.config != None:
            config.set_file(args.config)
        if args.env:
            config.add(load_env())
        config.set_args(args, dots=True)
    valid_config = config.get(template)
    return valid_config


def load_env():
    from os import environ

    confuse.ConfigSource.of(environ)

