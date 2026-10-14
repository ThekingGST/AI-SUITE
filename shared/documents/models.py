from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

@dataclass
class DocumentMetadata:
    title: str = ""
    author: str = ""
    creation_date: str = ""
    custom: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    source_reference: str = ""

@dataclass
class Document:
    doc_id: str
    filename: str
    mime_type: str
    size_bytes: int
    source_path: Optional[Path] = None
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    failed: bool = False
    error_reason: str = ""
    
    @property
    def full_text(self) -> str:
        return "\n\n".join(chunk.content for chunk in self.chunks)
