'''
Module that can be safely imported with the syntax
`from files.routes.importstar import *`. This essentially
contains flask stuff for routes that are used by pretty much
all routes.

This should only be used from the route handlers. Flask imports
are used in pretty much every place, but they shouldn't be used
from the models if at all possible.

Ideally we'd import only what we need but this is just for ease
of development. Feel free to remove.
'''

from flask import (Response, abort, g, jsonify, make_response, redirect,
                   render_template, request, send_file, send_from_directory,
                   session)
