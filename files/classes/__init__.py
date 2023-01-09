################################################################
#   WARNING! THIS FILE HAS A PERHAPS SLIGHTLY EVIL PRESENCE!   #
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
# This is being fixed now. Most things will probably not be    #
# importing the same things they were and we are much          #
# preferring explicit imports over implicit ones in order to   #
# get rid of import loops.                                     #
#                                                              #
################################################################

# First import our declarative base
from .base import Base

# Then let's define the models
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
from .usernotes import UserTag, UserNote
from .views import ViewerRelationship
from .votes import Vote, CommentVote
from .volunteer_janitor import VolunteerJanitorRecord
