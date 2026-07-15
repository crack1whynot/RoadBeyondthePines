from __future__ import annotations


class DocumentationService:
    """Service abstraction for documentation generation and storage."""

    def __init__(self) -> None:
        # TODO: implement markdown and structured docs pipeline.
        self.documents: list[str] = []

    def add_document(self, document_path: str) -> None:
        self.documents.append(document_path)
