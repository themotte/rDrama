'''
Module that can be safely imported with the syntax
`from files.routes.importstar import *`. This essentially
contains flask stuff for routes that are used by pretty much
all routes.

This should only be used from the route handlers. Flask imports
are used

Ideally we'd import only what we need but this is just for ease
of development. Feel free to remove.
'''

from flask import (abort, g, jsonify, make_response, redirect, render_template, 
                   request, Response, session, send_file, send_from_directory)