from typing import Protocol


class FileStorage(Protocol):
    def signed_download(self, storage_key: str, user_id: str) -> str: ...


class PushProvider(Protocol):
    def deliver(self, user_id: str, title: str, body: str) -> None: ...


class ConversationProvider(Protocol):
    """Phase 2 boundary only. No inference or knowledge schema in Phase 1."""

    def answer(self, user_id: str, question: str) -> dict: ...
