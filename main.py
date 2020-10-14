#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run server"""
import asyncio
import logging
import sys

from aiohttp import web

if __name__ == "__main__":
    from cherrydoor.app import setup_app
    from cherrydoor.interface.serial import Serial

    config = {}
    logging.basicConfig(
        level=config.get("log_level", logging.DEBUG),
        format="%(asctime)s:%(name)s:%(levelname)s: %(message)s",
    )
    loop = asyncio.get_event_loop()
    app = setup_app(loop, config)
    interface = Serial(app["db"], loop)
    app["serial"] = interface
    app.on_startup.append(interface.aiohttp_startup)
    app.on_cleanup.append(interface.cleanup)

    web.run_app(
        app,
        host=config.get("host", "127.0.0.1"),
        port=config.get("port", 5000),
        path=config.get("path", None),
    )
