#!/usr/bin/python3

import sys
import logging

sys.path.insert(0, '/var/www/html/chatbot')

from chatbot import app as application

logging.basicConfig(stream=sys.stderr)