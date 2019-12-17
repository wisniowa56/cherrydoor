#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run server"""
from cherrydoor import app, socket

__author__ = "opliko"
__license__ = "MIT"
__version__ = "0.1.2"
__status__ = "Prototype"

if __name__ == "__main__":
    # app.run(debug=True)
    socket.run(app, log_output=True)
