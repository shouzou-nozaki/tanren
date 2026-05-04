from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class UsageInfo:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseProvider(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def models(self) -> list[tuple[str, str]]: ...

    @property
    @abstractmethod
    def default_model(self) -> str: ...

    @abstractmethod
    def chat_stream(self, question: str, system: str, max_output_tokens: int = 1024):
        """text chunk を yield し、最後に UsageInfo を StopIteration で返す"""
        ...

    @abstractmethod
    def generate(self, prompt: str, system: str, max_output_tokens: int = 1024) -> tuple[str, UsageInfo]:
        """(text, UsageInfo) を返す"""
        ...
