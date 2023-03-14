# import our app then...
from files.__main__ import app

# import jinja2 helper then...
from files.helpers.jinja2 import *

# import allroutes then...
from files.routes.allroutes import *

# import routes :)
from .admin import *
from .comments import *
from .errors import *
from .reporting import *
from .front import *
from .login import *
from .oauth import *
from .posts import *
from .search import *
from .settings import *
from .static import *
from .users import *
from .votes import *
from .feeds import *
if FEATURES['AWARDS']:
	from .awards import * # disable entirely pending possible future use of coins
from .volunteer import *
if app.debug:
	from .dev import *
# from .subs import *
