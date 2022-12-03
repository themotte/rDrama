
from abc import ABC, abstractmethod

class VolunteerDuty(ABC):

    @abstractmethod
    def accept(self) -> None:
        pass

    @abstractmethod
    def embed_template(self) -> str:
        return ""
