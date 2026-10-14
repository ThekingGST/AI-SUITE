from typing import List, Dict, Tuple
from pathlib import Path
from .models import Document, DocumentChunk
from .parsers import ParserRegistry

class DocumentStore:
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.parser_registry = ParserRegistry()
        
    def attach_file(self, filepath: Path) -> Document:
        try:
            doc = self.parser_registry.parse_file(filepath)
            if not doc.chunks:
                doc.failed = True
                doc.error_reason = "No readable text extracted (may be image-based, encrypted, or empty)."
        except Exception as e:
            from .models import Document
            import uuid
            doc = Document(
                doc_id=str(uuid.uuid4()),
                filename=filepath.name,
                mime_type="application/octet-stream",
                size_bytes=filepath.stat().st_size if filepath.exists() else 0,
                source_path=filepath,
                failed=True,
                error_reason=str(e)
            )
        self.documents[doc.doc_id] = doc
        return doc
        
    def remove_file(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            del self.documents[doc_id]
            return True
        return False
        
    def get_all_chunks(self) -> List[Tuple[Document, DocumentChunk]]:
        chunks = []
        for doc in self.documents.values():
            if getattr(doc, 'failed', False):
                # We will handle failed docs directly in retrieve() instead of getting their chunks
                continue
            for chunk in doc.chunks:
                chunks.append((doc, chunk))
        return chunks

class Retriever:
    def __init__(self, store: DocumentStore):
        self.store = store
        
    def retrieve(self, query: str, top_k: int = 50, max_chars: int = 20000) -> str:
        chunks = self.store.get_all_chunks()
        failed_docs = [doc for doc in self.store.documents.values() if getattr(doc, 'failed', False)]
        
        if not chunks and not failed_docs:
            return ""
            
        # Basic keyword matching
        terms = set(query.lower().split()) - {"what", "is", "the", "in", "of", "a", "an", "to", "and", "this", "that", "these", "those"}
        
        scored_chunks = []
        for doc, chunk in chunks:
            content_lower = chunk.content.lower()
            doc_ext = doc.filename.split('.')[-1].lower() if '.' in doc.filename else ""
            score = 0
            
            if terms:
                score += sum(content_lower.count(term) for term in terms if len(term) > 2) * 2
                for term in terms:
                    if term in doc.filename.lower() or term == doc_ext or (term == "ppt" and doc_ext == "pptx") or (term == "word" and doc_ext == "docx") or (term == "excel" and doc_ext == "xlsx") or (term == "pdf" and doc_ext == "pdf"):
                        score += 50
            
            if score == 0:
                score = 0.1 # Base priority for all attached docs
                
            scored_chunks.append((score, doc, chunk))
            
        # Stable sort by score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        formatted = "<ATTACHED_DOCUMENTS>\n"
        
        # Inject failed docs first so the LLM always knows about them
        for fdoc in failed_docs:
            err = getattr(fdoc, 'error_reason', 'Unknown error')
            formatted += f"--- Document: {fdoc.filename} ---\n[STATUS: UNREADABLE. {err}]\n\n"
            
        current_chars = len(formatted)
        seen = set()
        
        for score, doc, chunk in scored_chunks:
            chunk_id = id(chunk)
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            
            chunk_str = f"--- Document: {doc.filename} | Source: {chunk.source_reference} ---\n<DOCUMENT_CONTENT>\n{chunk.content}\n</DOCUMENT_CONTENT>\n\n"
            
            if current_chars + len(chunk_str) > max_chars:
                formatted += f"--- Document: {doc.filename} | Source: {chunk.source_reference} ---\n<DOCUMENT_CONTENT>\n{chunk.content[:max_chars - current_chars - 100]}... [TRUNCATED DUE TO SIZE LIMIT]\n</DOCUMENT_CONTENT>\n"
                break
                
            formatted += chunk_str
            current_chars += len(chunk_str)
            
            top_k -= 1
            if top_k <= 0:
                break
                
        if not seen and not failed_docs:
            return ""
            
        formatted += "</ATTACHED_DOCUMENTS>"
        return formatted
