#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run server"""
from multiprocessing import Process
from cherrydoor import app, socket
from interface.commands import Commands

interface = Commands()
interface_run = Process(target=interface.start)
server = Process(target=socket.run, kwargs={"app": app, "log_output": True})


def exit():
    interface_run.terminate()
    server.terminate()


if __name__ == "__main__":
    import atexit

    atexit.register(exit)
    interface_run.start()
    server.run()
