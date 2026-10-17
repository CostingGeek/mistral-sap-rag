"""
Service for extracting requirements from text (PDF or transcript).
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from backend.integrations.mistral_client import MistralClient

logger = logging.getLogger(__name__)


class RequirementService:
    """
    Service for extracting discrete, testable requirements from text.
    """
    
    def __init__(self, mistral_client: MistralClient):
        self.mistral_client = mistral_client
    
    def extract_requirements(
        self,
        text: str,
        source_type: str = "pdf",
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract requirements from text.
        
        Args:
            text: The text to extract requirements from
            source_type: Type of source ('pdf' or 'transcript')
            page: Optional page number for PDF
        
        Returns:
            List of extracted requirements
        """
        prompt = f"""
Extract discrete, testable requirements from the following text.
Each requirement should be:
- A clear, specific statement of what is needed
- Testable (can be verified as implemented or not)
- Self-contained (doesn't reference other requirements)

Text (from {source_type}{' page ' + str(page) if page else ''}):
{text}

Format your response as a JSON array of requirement objects:
[{{ 
  "req_id": "R-01",  // Sequential ID
  "text": "The requirement text",
  "category": "optional category",  // e.g., "Functional", "Technical", "Compliance"
  "ref_in_doc": "optional reference",  // e.g., "Section 2.1" or page number
  "rationale": "optional extraction rationale"
}}]

Important:
- Deduplicate near-identical requirements
- Ignore boilerplate, introductory text, and non-requirement statements
- For transcripts, include speaker attribution if available
- Generate stable IDs (R-01, R-02, ...)

Return only the JSON array, no other text.
"""
        
        try:
            result = self.mistral_client.extract_json_response(
                prompt,
                schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "req_id": {"type": "string"},
                            "text": {"type": "string"},
                            "category": {"type": "string"},
                            "ref_in_doc": {"type": "string"},
                            "rationale": {"type": "string"}
                        },
                        "required": ["req_id", "text"]
                    }
                }
            )
            
            # Ensure result is a list
            if not isinstance(result, list):
                logger.warning(f"Mistral returned non-list result: {type(result)}. Using fallback.")
                return self._fallback_extract(text, source_type, page)
            
            requirements = []
            for i, req in enumerate(result):
                # Skip non-dict items
                if not isinstance(req, dict):
                    logger.warning(f"Skipping non-dict requirement at index {i}: {type(req)}")
                    continue
                    
                # Ensure req has text field
                if "text" not in req or not req["text"]:
                    logger.warning(f"Skipping requirement at index {i} with missing text: {req}")
                    continue
                
                # Ensure req_id follows R-XX format
                req_id = req.get("req_id", f"R-{i+1:02d}")
                if not req_id.startswith("R-"):
                    req_id = f"R-{i+1:02d}"
                
                # Deduplicate by text similarity
                is_duplicate = False
                for existing in requirements:
                    if self._text_similarity(req["text"], existing["text"]) > 0.9:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    req["req_id"] = req_id
                    requirements.append(req)
            
            return requirements
        
        except Exception as e:
            logger.error(f"Failed to extract requirements: {e}")
            # Fallback: split text into sentences as requirements
            return self._fallback_extract(text, source_type, page)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity (Jaccard similarity on words).
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union
    
    def _fallback_extract(
        self,
        text: str,
        source_type: str,
        page: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Fallback requirement extraction by splitting text into sentences.
        """
        import re
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        requirements = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
            
            requirements.append({
                "req_id": f"R-{i+1:02d}",
                "text": sentence,
                "category": "auto",
                "ref_in_doc": f"page {page}" if page else "auto"
            })
        
        return requirements
    
    def generate_requirement_id(
        self,
        text: str,
        session_id: str,
        index: int
    ) -> str:
        """
        Generate a deterministic requirement ID.
        
        Args:
            text: Requirement text
            session_id: Session ID
            index: Index within session
        
        Returns:
            A unique requirement ID
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{session_id}_R{index:03d}_{text_hash}"
