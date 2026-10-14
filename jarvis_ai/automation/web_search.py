import urllib.request
import urllib.error
from ddgs import DDGS
from jarvis_ai.utils.logger import LOGGER

class WebSearch:
    """Provides real-time web search and current information retrieval."""

    def __init__(self):
        self.ddgs = DDGS()

    def is_online(self) -> bool:
        try:
            import socket
            socket.create_connection(("1.1.1.1", 53), timeout=2)
            return True
        except OSError:
            return False
            
    def search(self, query: str, num_results: int = 5) -> list[str]:
        """Searches the web and returns a list of high-quality, deduplicated result snippets."""
        if not self.is_online():
            return []
            
        try:
            LOGGER.info("Performing web search for: %s", query)
            results = self.ddgs.text(query, max_results=num_results)
            snippets = []
            seen_bodies = set()
            
            for r in results:
                title = r.get('title', '').strip()
                body = r.get('body', '').strip()
                
                # Filter out empty, very short, or duplicate bodies
                if not title or not body or len(body) < 30:
                    continue
                    
                body_lower = body.lower()
                # Basic deduplication (if a body is a substring of another or vice versa)
                is_duplicate = False
                for seen in seen_bodies:
                    if body_lower in seen or seen in body_lower:
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    seen_bodies.add(body_lower)
                    snippets.append(f"{title}: {body}")
                    
                if len(snippets) >= 3:  # Only return the top 3 high quality ones
                    break
                    
            return snippets
        except Exception as e:
            LOGGER.error("Web search failed for query '%s': %s", query, e)
            return []
