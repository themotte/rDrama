################################################################
#                 WARNING! THIS FILE IS EVIL.                  #
################################################################
# Previously, this file had a series of                        #
#     from .alts import *                                      #
#     from .award import *                                     #
#     from .badges import *                                    #
# and so on in that fashion. That means that anywhere that     #
#     from files.classes import *                              #
# (and there were a lot of places like that) got anything      #
# was imported for any model imported. So if you, for example, #
# removed                                                      #
#     from secrets import token_hex                            #
# from files/classes/user.py, the registration page would      #
# break because files/routes/login.py did                      #
#     from files.classes import *                              #
# in order to get the token_hex function rather than           #
# importing it with something like                             #
#     from secrets import token_hex                            #
#                                                              #
# Anyway, not fixing that right now, but in order to           #
# what needed to be imported here such that                    #
#     from files.classes import *                              #
# still imported the same stuff as before I ran the following: #
#     $ find files/classes -type f -name '*.py' \              #
#         -exec grep import '{}' ';' \                         #
#         | grep 'import' \                                    #
#         | grep -v 'from [.]\|__init__\|from files.classes' \ #
#         | sed 's/^[^:]*://g' \                               #
#         | sort \                                             #
#         | uniq                                               #
# and then reordered the list such that import * did not stomp #
# over stuff that had been explicitly imported.                #
################################################################

# First the import * from places which don't go circular
from sqlalchemy import *
from flask import *

# Then everything except what's in files.*
import pyotp
import random
import re
import time
from copy import deepcopy
from datetime import datetime
from flask import g
from flask import render_template
from json import loads
from math import floor
from os import environ
from os import environ, remove, path
from random import randint
from secrets import token_hex
from sqlalchemy.orm import deferred, aliased
from sqlalchemy.orm import relationship
from sqlalchemy.orm import relationship, deferred
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.parse import urlparse

# It is now safe to define the models
from .alts import Alt
from .award import AwardRelationship
from .badges import BadgeDef, Badge
from .clients import OauthApp, ClientAuth
from .comment import Comment
from .domains import BannedDomain
from .exiles import Exile
from .flags import Flag, CommentFlag
from .follows import Follow
from .marsey import Marsey
from .mod import Mod
from .mod_logs import ModAction
from .notifications import Notification
from .saves import SaveRelationship, CommentSaveRelationship
from .sub import Sub
from .sub_block import SubBlock
from .submission import Submission
from .subscriptions import Subscription
from .user import User
from .userblock import UserBlock
from .views import ViewerRelationship
from .votes import Vote, CommentVote

# Then the import * from files.*
from files.helpers.const import *
from files.helpers.images import *
from files.helpers.lazy import *
from files.helpers.security import *

# Then the specific stuff we don't want stomped on
from files.helpers.discord import remove_user
from files.helpers.lazy import lazy
from files.__main__ import Base, app, cache
