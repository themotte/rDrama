
import enum

class StateMod(enum.Enum):
    VISIBLE = 0
    FILTERED = 1
    REMOVED = 2

class StateReport(enum.Enum):
    UNREPORTED = 0
    RESOLVED = 1
    REPORTED = 2
    IGNORED = 3
