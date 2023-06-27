
import enum

class StateMod(enum.Enum):
    Visible = 0
    Filtered = 1
    Removed = 2

class StateReport(enum.Enum):
    Unreported = 0
    Resolved = 1
    Reported = 2
    Ignored = 3
