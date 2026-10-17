"""
Service for generating fit-gap verdicts for requirements.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.integrations.bigquery_client import BigQueryClient
from backend.integrations.mistral_client import MistralClient
from backend.models.schemas import Verdict
from backend.services.requirement_service import RequirementService

logger = logging.getLogger(__name__)


class VerdictService:
    """
    Service for matching requirements against the corpus and generating verdicts.
    """
    
    def __init__(
        self,
        bq_client: BigQueryClient,
        mistral_client: MistralClient,
        requirement_service: RequirementService
    ):
        self.bq_client = bq_client
        self.mistral_client = mistral_client
        self.requirement_service = requirement_service
    
    def match_requirement(
        self,
        requirement: Dict[str, Any],
        session_id: str,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Match a single requirement against the corpus and generate a verdict.
        
        Args:
            requirement: The requirement to match
            session_id: Session ID for persistence
            model: Model to use for verdict
        
        Returns:
            Match result with verdict and rationale
        """
        req_id = requirement["req_id"]
        text = requirement["text"]
        
        # Step 1: Embed the requirement
        embedding = self.mistral_client.create_embedding(text)
        
        # Step 2: Retrieve similar chunks
        chunks = self.bq_client.retrieve_similar_chunks(
            embedding,
            top_k=settings.retrieval_k
        )
        
        # Step 3: Group hits by object and fetch evidence
        object_groups = {}
        for chunk in chunks:
            obj_id = chunk["object_id"]
            if obj_id not in object_groups:
                object_groups[obj_id] = {
                    "chunks": [],
                    "min_distance": chunk["distance"],
                    "sections": {}
                }
            
            object_groups[obj_id]["chunks"].append(chunk)
            object_groups[obj_id]["min_distance"] = min(
                object_groups[obj_id]["min_distance"],
                chunk["distance"]
            )
            
            # Fetch full object info for evidence
            if chunk["section_type"] not in object_groups[obj_id]["sections"]:
                obj_info = self.bq_client.get_object_info(obj_id)
                if obj_info:
                    for section_type, content in obj_info.get("sections", {}).items():
                        if section_type in ["USE", "SHORTTEXT", "PRECONDITIONS"]:
                            object_groups[obj_id]["sections"][section_type] = content
        
        # Step 4: Filter to only embed-eligible objects with good matches
        good_matches = []
        for obj_id, data in object_groups.items():
            if data["min_distance"] < settings.similarity_threshold:
                good_matches.append({
                    "object_id": obj_id,
                    "distance": data["min_distance"],
                    "sections": data["sections"]
                })
        
        good_matches.sort(key=lambda x: x["distance"])
        
        # Step 5: Generate verdict using LLM
        evidence_context = self._build_evidence_context(good_matches)
        
        verdict_result = self._generate_verdict(
            text,
            evidence_context,
            good_matches
        )
        
        # Step 6: Determine final verdict based on evidence
        final_verdict = self._determine_final_verdict(
            verdict_result,
            good_matches
        )
        
        # Build match result
        matched_objects = [m["object_id"] for m in good_matches]
        
        return {
            "req_id": req_id,
            "session_id": session_id,
            "object_id": good_matches[0]["object_id"] if good_matches else None,
            "distance": good_matches[0]["distance"] if good_matches else 1.0,
            "verdict": final_verdict,
            "rationale": verdict_result.get("rationale", ""),
            "model": model or settings.chat_model,
            "matched_objects": matched_objects,
            "open_questions": verdict_result.get("open_questions", []),
            "decision_needed": verdict_result.get("decision_needed", False),
            "decision_question": verdict_result.get("decision_question"),
            "decision_options": verdict_result.get("decision_options", [])
        }
    
    def _build_evidence_context(self, matches: List[Dict[str, Any]]) -> str:
        """
        Build a context string from matched objects for the LLM.
        """
        if not matches:
            return "No matching documentation found."
        
        context_parts = []
        for i, match in enumerate(matches):
            context_parts.append(f"\nMatch {i+1}: {match['object_id']}")
            context_parts.append(f"Distance: {match['distance']:.4f}")
            
            for section_type, content in match["sections"].items():
                context_parts.append(f"\n{section_type}:{content[:500]}")
        
        return "\n".join(context_parts)
    
    def _generate_verdict(
        self,
        requirement_text: str,
        evidence_context: str,
        matches: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a verdict using the LLM.
        """
        has_matches = len(matches) > 0 and matches[0]["distance"] < settings.similarity_threshold
        
        prompt = f"""
Analyze the following requirement against the SAP Customizing documentation.

Requirement: {requirement_text}

Evidence from Documentation:
{evidence_context}

Classification:
Based on the evidence, classify this requirement as one of:
- "fit": The requirement is fully covered by standard SAP Customizing
- "partial": The requirement is partially covered, but configuration choices remain
- "gap": The requirement is NOT covered by standard Customizing
- "question": Cannot determine from available evidence

Additionally:
- If the verdict is "partial" or "question", identify any open questions that need workshop discussion
- If there are scope ambiguities (e.g., country scope, deployment type), flag a decision

Provide your analysis as JSON:
{{
  "verdict": "fit|partial|gap|question",
  "rationale": "Explanation of why this verdict was chosen",
  "open_questions": ["list", "of", "questions"],
  "decision_needed": true/false,
  "decision_question": "What needs to be decided?",
  "decision_options": ["option1", "option2"]
}}

Important:
- Base your verdict ONLY on the evidence provided
- Be specific about what is covered and what is not
- Identify configuration choices for "partial" verdicts
"""
        
        try:
            result = self.mistral_client.extract_json_response(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "verdict": {"type": "string", "enum": ["fit", "partial", "gap", "question"]},
                        "rationale": {"type": "string"},
                        "open_questions": {"type": "array", "items": {"type": "string"}},
                        "decision_needed": {"type": "boolean"},
                        "decision_question": {"type": "string"},
                        "decision_options": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["verdict", "rationale"]
                }
            )
            return result
        except Exception as e:
            logger.error(f"Failed to generate verdict: {e}")
            # Fallback: determine verdict based on match quality
            return {
                "verdict": "question",
                "rationale": f"Could not generate automated verdict: {e}",
                "open_questions": [],
                "decision_needed": False
            }
    
    def _determine_final_verdict(
        self,
        verdict_result: Dict[str, Any],
        matches: List[Dict[str, Any]]
    ) -> str:
        """
        Determine the final verdict, potentially overriding the LLM verdict
        based on match quality.
        """
        # If LLM says "fit" or "partial" but there are no good matches, override to "question"
        if verdict_result.get("verdict") in ["fit", "partial"] and not matches:
            return Verdict.QUESTION.value
        
        # If LLM says "fit" but the best match distance is too high, override
        if verdict_result.get("verdict") == "fit" and matches:
            if matches[0]["distance"] > 0.4:  # Threshold from spec
                return Verdict.QUESTION.value
        
        return verdict_result.get("verdict", Verdict.QUESTION.value)
    
    def match_requirements_batch(
        self,
        requirements: List[Dict[str, Any]],
        session_id: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Match a batch of requirements.
        
        Args:
            requirements: List of requirements to match
            session_id: Session ID
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of match results
        """
        results = []
        
        for i, req in enumerate(requirements):
            result = self.match_requirement(req, session_id)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(requirements), result)
        
        return results
