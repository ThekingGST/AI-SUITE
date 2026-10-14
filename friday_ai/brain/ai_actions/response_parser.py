"""Response Parser: Extracts structured elements from raw AI responses."""

from __future__ import annotations
from dataclasses import dataclass, field
import re


@dataclass
class ParsedAIResponse:
    """Structured data extracted from an AI response."""
    raw_text: str
    markdown: str
    code_blocks: list[dict[str, str]] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    language_detected: str = ""
    # In the future, this can hold DiffProposals
    diff_candidates: list[object] = field(default_factory=list)


class ResponseParser:
    """Parses streaming or completed AI responses into structured formats."""

    @staticmethod
    def parse(response_text: str) -> ParsedAIResponse:
        """Parse full markdown text into a structured response."""
        
        parsed = ParsedAIResponse(
            raw_text=response_text,
            markdown=response_text
        )
        
        # Extremely basic regex to find code blocks: ```language ... ```
        block_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        blocks = block_pattern.findall(response_text)
        
        for lang, content in blocks:
            parsed.code_blocks.append({
                "language": lang.strip(),
                "content": content.strip()
            })
            if lang and not parsed.language_detected:
                parsed.language_detected = lang.strip()
                
        # Split explanations by assuming non-code text is explanation
        explanation_text = re.sub(block_pattern, "", response_text).strip()
        if explanation_text:
            parsed.explanations = [p.strip() for p in explanation_text.split("\n\n") if p.strip()]
            
        return parsed
