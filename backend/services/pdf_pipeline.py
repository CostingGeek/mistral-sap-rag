"""
PDF processing pipeline for fit-gap analysis.
"""
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from backend.config import settings
from backend.integrations.bigquery_client import BigQueryClient
from backend.integrations.gcs_client import GCSClient
from backend.integrations.mistral_client import MistralClient
from backend.models.schemas import SessionKind, SessionStatus, Verdict
from backend.services.decision_service import DecisionService
from backend.services.requirement_service import RequirementService
from backend.services.verdict_service import VerdictService

logger = logging.getLogger(__name__)


class PDFPipeline:
    """
    Pipeline for processing PDF documents for fit-gap analysis.
    """
    
    def __init__(
        self,
        bq_client: BigQueryClient,
        mistral_client: MistralClient,
        gcs_client: GCSClient,
        requirement_service: RequirementService,
        verdict_service: VerdictService,
        decision_service: DecisionService
    ):
        self.bq_client = bq_client
        self.mistral_client = mistral_client
        self.gcs_client = gcs_client
        self.requirement_service = requirement_service
        self.verdict_service = verdict_service
        self.decision_service = decision_service
    
    def process_pdf(
        self,
        file_path: Union[str, Path],
        session_id: str,
        title: str,
        progress_callback: Optional[Callable[[str, int, int, Dict], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a PDF file through the full pipeline.
        
        Args:
            file_path: Path to the PDF file
            session_id: Session ID
            title: Session title
            progress_callback: Optional callback for progress updates
        
        Returns:
            Pipeline result with requirements, matches, decisions
        """
        total_steps = 5
        current_step = 0
        
        result = {
            "session_id": session_id,
            "status": "completed",
            "requirements": [],
            "matches": [],
            "decisions": [],
            "summary": "",
            "stats": {}
        }
        
        try:
            # Step 1: Upload to GCS (optional - skip if GCS not configured or fails)
            current_step += 1
            if progress_callback:
                progress_callback("uploading", current_step, total_steps, {"status": "uploading"})
            
            gcs_uri = None
            try:
                gcs_uri = self._upload_to_gcs(file_path, session_id)
                logger.info(f"Uploaded PDF to GCS: {gcs_uri}")
            except Exception as e:
                logger.warning(f"GCS upload skipped (no credentials or permission): {e}")
            
            result["source_ref"] = gcs_uri or f"local:{file_path}"
            
            # Step 2: OCR extraction
            current_step += 1
            if progress_callback:
                progress_callback("extracting_text", current_step, total_steps, {"status": "extracting"})
            
            pages_text = self._extract_text_from_pdf(file_path)
            
            # Step 3: Requirement extraction
            current_step += 1
            if progress_callback:
                progress_callback("extracting_requirements", current_step, total_steps, {"status": "extracting", "page_count": len(pages_text)})
            
            requirements = self._extract_requirements_from_pages(pages_text, session_id)
            result["requirements"] = requirements
            
            # Persist requirements to BigQuery
            self._persist_requirements(requirements, session_id)
            
            # Step 4: Per-requirement matching
            current_step += 1
            if progress_callback:
                progress_callback("matching", current_step, total_steps, {"status": "matching", "req_count": len(requirements)})
            
            matches = []
            for req in requirements:
                match = self.verdict_service.match_requirement(req, session_id)
                matches.append(match)
                
                if progress_callback:
                    progress_callback("matching", current_step, total_steps, {
                        "status": "matching",
                        "progress": len(matches),
                        "total": len(requirements),
                        "current_req": req["req_id"]
                    })
            
            result["matches"] = matches
            
            # Persist matches to BigQuery
            self._persist_matches(matches, session_id)
            
            # Step 5: Decision generation
            current_step += 1
            if progress_callback:
                progress_callback("generating_decisions", current_step, total_steps, {"status": "generating"})
            
            decisions = []
            for req, match in zip(requirements, matches):
                req_decisions = self.decision_service.generate_decisions(
                    req, match, session_id
                )
                decisions.extend(req_decisions)
            
            # Group similar decisions
            decisions = self.decision_service.group_similar_decisions(decisions)
            
            # Persist decisions to BigQuery
            self._persist_decisions(decisions, session_id)
            
            result["decisions"] = decisions
            
            # Generate summary
            result["summary"] = self._generate_summary(requirements, matches, decisions)
            result["stats"] = self._generate_stats(requirements, matches, decisions)
            
            # Update session status
            self.bq_client.update_session_status(session_id, "completed")
            
            return result
        
        except Exception as e:
            logger.error(f"PDF pipeline failed: {e}")
            self.bq_client.update_session_status(session_id, "failed")
            raise
    
    def _upload_to_gcs(self, file_path: Union[str, Path], session_id: str) -> str:
        """Upload PDF to GCS."""
        destination = f"uploads/{session_id}/input.pdf"
        return self.gcs_client.upload_file(file_path, destination, content_type="application/pdf")
    
    def _extract_text_from_pdf(self, file_path: Union[str, Path]) -> List[Tuple[int, str]]:
        """
        Extract text from each page of a PDF using Mistral OCR.
        
        Returns:
            List of (page_number, text) tuples
        """
        # For PDFs, we need to handle them page by page
        # Since Mistral OCR API handles PDFs directly, we can use that
        
        try:
            text = self.mistral_client.ocr_document(file_path)
            # If the OCR returns text for the whole document, we'll split it
            # For now, treat the whole document as one "page"
            return [(1, text)]
        except Exception as e:
            logger.warning(f"Mistral OCR failed, trying pypdf fallback: {e}")
            # Fallback: use pypdf to extract text from PDF
            try:
                from pypdf import PdfReader
                
                reader = PdfReader(file_path)
                pages_text = []
                for i, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append((i, page_text))
                
                if pages_text:
                    return pages_text
                else:
                    raise ValueError("No text found in PDF using pypdf")
                    
            except ImportError:
                logger.warning("pypdf not available, trying basic text read")
                # Last resort: try to read as text (won't work for binary PDFs)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    return [(1, text)]
                except Exception as e2:
                    raise ValueError(f"Could not extract text from PDF: {e}") from e2
            except Exception as e2:
                raise ValueError(f"Could not extract text from PDF using pypdf: {e2}") from e2
    
    def _extract_requirements_from_pages(
        self,
        pages_text: List[Tuple[int, str]],
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract requirements from all pages.
        
        Args:
            pages_text: List of (page_number, text) tuples
            session_id: Session ID
        
        Returns:
            List of requirement objects
        """
        all_requirements = []
        
        for page_num, text in pages_text:
            # Split text into manageable chunks for LLM
            chunks = self._split_text_for_llm(text)
            
            for i, chunk in enumerate(chunks):
                reqs = self.requirement_service.extract_requirements(
                    chunk,
                    source_type="pdf",
                    page=page_num
                )
                
                for req in reqs:
                    # Generate a unique ID
                    req_id = self.requirement_service.generate_requirement_id(
                        req["text"],
                        session_id,
                        len(all_requirements) + 1
                    )
                    req["req_id"] = req_id
                    req["page"] = page_num
                    req["session_id"] = session_id
                    req["created_at"] = datetime.utcnow().isoformat()
                    
                    all_requirements.append(req)
        
        return all_requirements
    
    def _split_text_for_llm(self, text: str, max_length: int = 4000) -> List[str]:
        """
        Split text into chunks suitable for LLM processing.
        """
        # Simple split by paragraphs first
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 < max_length:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _persist_requirements(self, requirements: List[Dict[str, Any]], session_id: str) -> None:
        """Persist requirements to BigQuery."""
        for req in requirements:
            self.bq_client.create_requirement(
                req_id=req["req_id"],
                session_id=session_id,
                text=req["text"],
                ref_in_doc=req.get("ref_in_doc"),
                category=req.get("category"),
                page=req.get("page")
            )
    
    def _persist_matches(self, matches: List[Dict[str, Any]], session_id: str) -> None:
        """Persist matches to BigQuery."""
        for match in matches:
            self.bq_client.create_match(
                req_id=match["req_id"],
                session_id=session_id,
                object_id=match["object_id"],
                distance=match["distance"],
                verdict=match["verdict"],
                rationale=match["rationale"],
                model=match["model"],
                matched_objects=match["matched_objects"]
            )
    
    def _persist_decisions(self, decisions: List[Dict[str, Any]], session_id: str) -> None:
        """Persist decisions to BigQuery."""
        for i, decision in enumerate(decisions):
            decision_id = f"{session_id}_D{i+1:03d}"
            self.bq_client.create_decision(
                decision_id=decision_id,
                session_id=session_id,
                question=decision["question"],
                req_id=decision.get("req_id"),
                options=decision.get("options", []),
                source=decision.get("source", "pdf")
            )
    
    def _generate_summary(
        self,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]]
    ) -> str:
        """Generate an executive summary of the fit-gap analysis."""
        
        # Count verdicts
        verdict_counts = {v.value: 0 for v in Verdict}
        for match in matches:
            verdict = match.get("verdict")
            if verdict in verdict_counts:
                verdict_counts[verdict] += 1
        
        total_requirements = len(requirements)
        
        summary = f"""
# Fit-Gap Analysis Summary

## Overview
Analyzed **{total_requirements} requirements** against the SAP Customizing documentation.

## Coverage Statistics
- **Fit**: {verdict_counts['fit']} requirements ({100 * verdict_counts['fit'] / total_requirements:.1f}%)
- **Partial**: {verdict_counts['partial']} requirements ({100 * verdict_counts['partial'] / total_requirements:.1f}%)
- **Gap**: {verdict_counts['gap']} requirements ({100 * verdict_counts['gap'] / total_requirements:.1f}%)
- **Question**: {verdict_counts['question']} requirements ({100 * verdict_counts['question'] / total_requirements:.1f}%)

## Key Findings
"""
        
        # Add biggest gaps
        gaps = [m for m in matches if m.get("verdict") == "gap"]
        if gaps:
            summary += "\n### Major Gaps\n"
            for gap in gaps[:5]:  # Top 5 gaps
                req = next((r for r in requirements if r["req_id"] == gap["req_id"]), None)
                if req:
                    summary += f"- **{req['text'][:100]}...**\n"
                    summary += f"  *No matching SAP Customizing activity found*\n\n"
        
        # Add decisions
        if decisions:
            summary += "\n## Open Decisions\n"
            for decision in decisions[:10]:  # Top 10 decisions
                summary += f"- **{decision['question']}**\n"
                if decision.get("options"):
                    summary += f"  Options: {', '.join(decision['options'])} \n"
        
        # Add recommendations
        summary += "\n## Recommended Workshop Agenda\n"
        if verdict_counts['partial'] > 0:
            summary += f"1. Review {verdict_counts['partial']} partial matches for configuration choices\n"
        if verdict_counts['gap'] > 0:
            summary += f"2. Address {verdict_counts['gap']} gaps - identify custom development or alternative solutions\n"
        if decisions:
            summary += f"3. Discuss {len(decisions)} open decisions (see above)\n"
        
        return summary
    
    def _generate_stats(
        self,
        requirements: List[Dict[str, Any]],
        matches: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate statistics from the analysis."""
        verdict_counts = {v.value: 0 for v in Verdict}
        for match in matches:
            verdict = match.get("verdict")
            if verdict in verdict_counts:
                verdict_counts[verdict] += 1
        
        total_requirements = len(requirements)
        
        return {
            "total_requirements": total_requirements,
            "verdict_counts": verdict_counts,
            "decision_count": len(decisions),
            "coverage_percentage": 100 * (verdict_counts['fit'] + verdict_counts['partial']) / total_requirements if total_requirements > 0 else 0,
            "gap_percentage": 100 * verdict_counts['gap'] / total_requirements if total_requirements > 0 else 0
        }
