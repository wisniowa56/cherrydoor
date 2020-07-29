#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run server"""
from multiprocessing import Process
from cherrydoor.server import app, socket, config
from cherrydoor.interface.commands import Commands
import sys

interface = Commands()
interface_run = Process(target=interface.start)
server = Process(
    target=socket.run,
    kwargs={
        "app": app,
        "log_output": True,
        "host": config["host"],
        "port": config["port"],
    },
)


def exit():
    print("Closing server and serial connections")
    interface_run.terminate()
    sys.exit()


if __name__ == "__main__":
    import atexit

    atexit.register(exit)
    interface_run.start()
    server.run()
