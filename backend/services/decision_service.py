"""
Service for managing decisions from fit-gap analysis.
"""
import logging
from typing import Any, Dict, List, Optional

from backend.integrations.mistral_client import MistralClient

logger = logging.getLogger(__name__)


class DecisionService:
    """
    Service for generating and managing decisions from fit-gap analysis.
    """
    
    def __init__(self, mistral_client: MistralClient):
        self.mistral_client = mistral_client
    
    def generate_decisions(
        self,
        requirement: Dict[str, Any],
        match_result: Dict[str, Any],
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Generate decisions from a requirement and its match result.
        
        Args:
            requirement: The requirement
            match_result: The match result with verdict
            session_id: Session ID
        
        Returns:
            List of decision objects
        """
        decisions = []
        
        # If the match indicates a decision is needed
        if match_result.get("decision_needed"):
            decisions.append({
                "session_id": session_id,
                "req_id": requirement["req_id"],
                "question": match_result.get("decision_question", ""),
                "options": match_result.get("decision_options", []),
                "source": "pdf" if requirement.get("source_type") == "pdf" else "manual"
            })
        
        # Check for scope ambiguities in the requirement text
        scope_decisions = self._extract_scope_decisions(requirement["text"])
        for decision in scope_decisions:
            decisions.append({
                "session_id": session_id,
                "req_id": requirement["req_id"],
                **decision
            })
        
        return decisions
    
    def _extract_scope_decisions(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract scope-related decisions from requirement text.
        
        Args:
            text: Requirement text
        
        Returns:
            List of scope decision objects
        """
        import re
        
        decisions = []
        text_lower = text.lower()
        
        # Check for country/region scope
        if any(word in text_lower for word in ["country", "countries", "region", "regions", "global", "international"]):
            decisions.append({
                "question": "Which countries are in scope for this requirement?",
                "options": ["DE/FR only", "EU", "Global", "Specific countries to be determined"],
                "source": "auto-detected"
            })
        
        # Check for deployment scope
        if any(word in text_lower for word in ["cloud", "on-premise", "on premise", "deployment"]):
            decisions.append({
                "question": "Is this requirement for cloud or on-premise deployment?",
                "options": ["Cloud", "On-Premise", "Both"],
                "source": "auto-detected"
            })
        
        # Check for regulatory scope
        if any(word in text_lower for word in ["compliance", "regulation", "regulatory", "dg", "dangerous goods"]):
            decisions.append({
                "question": "Which regulations apply to this requirement?",
                "options": ["UN Regulations", "EU Regulations", "Local Regulations", "Multiple - to be determined"],
                "source": "auto-detected"
            })
        
        # Check for organization scope
        if any(word in text_lower for word in ["organization", "org", "company", "legal entity", "plant"]):
            decisions.append({
                "question": "Which organizational units are in scope?",
                "options": ["All units", "Specific units to be determined", "Headquarters only"],
                "source": "auto-detected"
            })
        
        return decisions
    
    def group_similar_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group similar decisions together to avoid duplicates.
        
        Args:
            decisions: List of decision objects
        
        Returns:
            List of grouped decision objects
        """
        grouped = []
        seen_questions = set()
        
        for decision in decisions:
            question = decision["question"]
            
            # Check if this question is similar to any existing
            found = False
            for existing in grouped:
                if self._questions_similar(existing["question"], question):
                    # Merge options
                    existing_options = set(existing.get("options", []))
                    new_options = decision.get("options", [])
                    merged_options = list(existing_options | set(new_options))
                    existing["options"] = merged_options
                    found = True
                    break
            
            if not found:
                grouped.append(decision)
        
        return grouped
    
    def _questions_similar(self, q1: str, q2: str, threshold: float = 0.7) -> bool:
        """
        Check if two questions are similar based on word overlap.
        """
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return (intersection / union) >= threshold
    
    def match_transcript_to_decisions(
        self,
        transcript_text: str,
        open_decisions: List[Dict[str, Any]],
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Match transcript text against open decisions to determine their status.
        
        Args:
            transcript_text: The transcript text
            open_decisions: List of open decisions
            session_id: Session ID
        
        Returns:
            List of updated decision objects with status
        """
        results = []
        
        for decision in open_decisions:
            decision_id = decision.get("decision_id", decision.get("id", ""))
            question = decision["question"]
            options = decision.get("options", [])
            
            # Check if the decision is discussed in the transcript
            status_result = self._check_decision_in_transcript(
                transcript_text,
                question,
                options
            )
            
            result = {
                "decision_id": decision_id,
                "session_id": session_id,
                "question": question,
                "options": options,
                "status": status_result["status"],
                "answer": status_result.get("answer"),
                "evidence": status_result.get("evidence", "")
            }
            
            results.append(result)
        
        return results
    
    def _check_decision_in_transcript(
        self,
        transcript_text: str,
        question: str,
        options: List[str]
    ) -> Dict[str, Any]:
        """
        Check if a decision is answered or discussed in the transcript.
        
        Args:
            transcript_text: The transcript text
            question: The decision question
            options: The decision options
        
        Returns:
            Status result with answer if found
        """
        prompt = f"""
Analyze the following transcript for evidence related to this decision.

Decision Question: {question}

Options:
{chr(10).join([f'- {opt}' for opt in options]) if options else 'None'}

Transcript:
{transcript_text[:4000]}

Classification:
Determine if this decision was addressed in the transcript:
- "answered": The question was directly answered and the answer is clear
- "discussed": The question was discussed but no clear answer was given
- "not_discussed": The question was not mentioned or discussed

If answered, extract:
- The answer chosen (or most likely answer)
- A quote from the transcript as evidence
- Who answered (if speaker information is available)

Return your analysis as JSON:
{{
  "status": "answered|discussed|not_discussed",
  "answer": "the answer if status is answered",
  "evidence": "a quote from the transcript as evidence",
  "speaker": "who answered if available"
}}
"""
        
        try:
            result = self.mistral_client.extract_json_response(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["answered", "discussed", "not_discussed"]},
                        "answer": {"type": "string"},
                        "evidence": {"type": "string"},
                        "speaker": {"type": "string"}
                    },
                    "required": ["status"]
                }
            )
            return result
        except Exception as e:
            logger.error(f"Failed to check decision in transcript: {e}")
            return {"status": "not_discussed"}
