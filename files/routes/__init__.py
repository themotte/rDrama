from files.__main__ import app

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
from .awards import *
from .giphy import *
from .volunteer import *
if app.debug:
	from .dev import *
# from .subs import *
