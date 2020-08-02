#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run server"""
from multiprocessing import Process
from cherrydoor.interface.serial import Serial
import sys
from time import sleep

interface = Serial()
interface_run = Process(target=interface.start)


def exit():
    print("Closing server and serial connections")
    interface_run.terminate()
    sys.exit()


if __name__ == "__main__":
    import atexit

    interface_run.start()
    sleep(2)
    atexit.register(exit)
    from cherrydoor.server import app, socket, config

    server = Process(
        target=socket.run,
        kwargs={
            "app": app,
            "log_output": True,
            "host": config["host"],
            "port": config["port"],
        },
    )
    server.run()
