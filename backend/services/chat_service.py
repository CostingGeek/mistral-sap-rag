"""
Chat service for agentic retrieval and conversation.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.integrations.bigquery_client import BigQueryClient
from backend.integrations.mistral_client import MistralClient
from backend.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChunkInfo,
)

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for handling chat interactions with agentic retrieval.
    """
    
    def __init__(
        self,
        bq_client: BigQueryClient,
        mistral_client: MistralClient
    ):
        self.bq_client = bq_client
        self._object_info_cache: Dict[str, Optional[Dict[str, Any]]] = {}
        self.mistral_client = mistral_client
    
    def classify_intent(self, question: str) -> Dict[str, Any]:
        """
        Classify the intent of a question.
        
        Args:
            question: The user's question
        
        Returns:
            Intent classification with potential sub-queries
        """
        prompt = f"""
Classify the following question and determine if it should be decomposed into sub-queries.

Question: {question}

Classification:
- If the question is simple and can be answered with a single search, return: {{"type": "simple", "query": "<original question>"}}
- If the question spans multiple domains or has multiple sub-intents, return: {{"type": "multi_intent", "sub_queries": ["<sub-query 1>", "<sub-query 2>", ...]}}
- If the question is a follow-up to a previous conversation, return: {{"type": "follow_up", "query": "<reformulated question with context>"}}

Return only the JSON object, no other text.
"""
        
        try:
            result = self.mistral_client.extract_json_response(
                prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["simple", "multi_intent", "follow_up"]},
                        "query": {"type": "string"},
                        "sub_queries": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
            return result
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, using simple query")
            return {"type": "simple", "query": question}
    
    def retrieve_chunks(
        self,
        query: str,
        top_k: int = None,
        section_filter: Optional[str] = None,
        scope: str = "both"
    ) -> List[ChunkInfo]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: The search query
            top_k: Number of chunks to retrieve
            section_filter: Optional filter for section_type
        
        Returns:
            List of chunk information with similarity scores
        """
        top_k = top_k or settings.retrieval_k
        
        # Create embedding for the query
        embedding = self.mistral_client.create_embedding(query)
        
        # Retrieve similar chunks
        results = self.bq_client.retrieve_similar_chunks(
            embedding,
            top_k=top_k,
            section_filter=section_filter,
            scope=scope
        )
        
        return [
            ChunkInfo(
                chunk_id=row["chunk_id"],
                object_id=row["object_id"],
                title=row["title"],
                section_type=row["section_type"],
                distance=row["distance"],
                content=row["content"]
            )
            for row in results
        ]
    
    def expand_graph(
        self,
        chunks: List[ChunkInfo],
        hops: int = 1,
        scope: str = "both"
    ) -> Tuple[List[ChunkInfo], List[Dict[str, Any]]]:
        """
        Expand the retrieval by following graph edges (element_refs).
        
        Args:
            chunks: Initial chunks to expand from
            hops: Number of hops to follow
        
        Returns:
            Tuple of (expanded chunks, graph edges)
        """
        object_ids = {c.object_id for c in chunks}
        edges = []
        additional_chunks = []
        
        for hop in range(hops):
            # Get references for each object
            for object_id in object_ids:
                graph = self.bq_client.get_related_objects(object_id, depth=1, scope=scope)
                
                for edge in graph["edges"]:
                    edges.append(edge)
                    
                    # Get chunks for the related object
                    if edge["target"] not in object_ids:
                        obj_id = edge["target"]
                        cache_key = f"{scope}:{obj_id}"
                        if cache_key not in self._object_info_cache:
                            self._object_info_cache[cache_key] = self.bq_client.get_object_info(obj_id, scope=scope)
                        obj_info = self._object_info_cache[cache_key]
                        if obj_info and obj_info.get("sections"):
                            # Create chunks for USE and SHORTTEXT sections
                            for section_type, content in obj_info["sections"].items():
                                if section_type in ["USE", "SHORTTEXT"]:
                                    chunk_id = f"{edge['target']}::{section_type}"
                                    additional_chunks.append(
                                        ChunkInfo(
                                            chunk_id=chunk_id,
                                            object_id=edge["target"],
                                            title=obj_info["title"],
                                            section_type=section_type,
                                            distance=0.0,  # Not applicable for graph-expanded chunks
                                            content=content
                                        )
                                    )
            
            object_ids.update({c.object_id for c in additional_chunks})
        
        # Combine original and additional chunks, deduplicate by chunk_id
        all_chunks = chunks + additional_chunks
        seen_chunk_ids = set()
        unique_chunks = []
        
        for chunk in all_chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)
        
        return unique_chunks, edges
    
    def synthesize_answer(
        self,
        query: str,
        chunks: List[ChunkInfo],
        history: Optional[List[ChatMessage]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Synthesize an answer from retrieved chunks.
        
        Args:
            query: The user's query
            chunks: Retrieved chunks with context
            history: Optional conversation history
        
        Returns:
            Tuple of (answer text, citations)
        """
        # Build the context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(
                f"Source {i+1} (Object: {chunk.object_id}, Section: {chunk.section_type}, Distance: {chunk.distance:.4f}):\n"
                f"{chunk.title}\n"
                f"{chunk.content}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Build messages with history
        messages = []
        
        if history:
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({
            "role": "user",
            "content": query
        })
        
        # System prompt for grounded answers
        system_prompt = f"""
You are an expert SAP Customizing consultant. Answer the user's question based ONLY on the provided context.

Context:
{context}

Guidelines:
- Every claim must be supported by the context
- Cite sources using the format: [Source N] where N is the source number
- If the context doesn't contain enough information, say so explicitly
- Be specific and detailed in your answers
- Use technical SAP terminology

Now answer the user's question.
"""
        
        messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Get chat completion
        result = self.mistral_client.chat_completion(
            messages,
            temperature=0.3,
            max_tokens=4096
        )
        
        if "choices" in result and len(result["choices"]) > 0:
            answer = result["choices"][0]["message"]["content"]
        else:
            answer = "I apologize, but I couldn't generate an answer based on the available information."
        
        # Extract citations from the answer
        citations = []
        for i, chunk in enumerate(chunks):
            if f"[Source {i+1}]" in answer:
                citations.append({
                    "chunk_id": chunk.chunk_id,
                    "object_id": chunk.object_id,
                    "title": chunk.title,
                    "section_type": chunk.section_type,
                    "distance": chunk.distance
                })
        
        return answer, citations
    
    def chat(
        self,
        request: ChatRequest,
        session_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat request with agentic retrieval.
        
        Args:
            request: The chat request
            session_id: Optional session ID for persistence
        
        Returns:
            Chat response with answer and citations
        """
        query = request.message
        top_k = request.top_k or settings.retrieval_k
        history = request.history or []
        scope = request.scope or "both"
        if scope not in self.bq_client.VALID_SCOPES:
            raise ValueError(f"Invalid scope: {scope}. Must be one of {self.bq_client.VALID_SCOPES}")
        
        # Step 1: Intent classification
        intent = self.classify_intent(query)
        trace = [{"step": "intent_classification", "result": intent}]
        
        # Step 2: Generate queries
        if intent["type"] == "multi_intent":
            queries = intent["sub_queries"]
            trace.append({"step": "query_decomposition", "queries": queries})
        else:
            queries = [intent.get("query", query)]
        
        # Step 3: Retrieve chunks for each query
        all_chunks = []
        for q in queries:
            chunks = self.retrieve_chunks(q, top_k=top_k // len(queries), scope=scope)
            all_chunks.extend(chunks)
            trace.append({
                "step": "retrieval",
                "query": q,
                "chunk_count": len(chunks)
            })
        
        # Deduplicate chunks
        seen_chunk_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)
        
        all_chunks = unique_chunks
        
        # Step 4: Graph expansion
        expanded_chunks, edges = self.expand_graph(all_chunks, hops=1, scope=scope)
        trace.append({
            "step": "graph_expansion",
            "original_count": len(all_chunks),
            "expanded_count": len(expanded_chunks),
            "edge_count": len(edges)
        })
        
        # Step 5: Synthesize answer
        answer, citations = self.synthesize_answer(
            query,
            expanded_chunks,
            history
        )
        
        # Build matched objects
        matched_objects = list({c.object_id for c in expanded_chunks})
        
        # Build graph data
        graph_data = {
            "nodes": [{"id": c.object_id, "title": c.title} for c in expanded_chunks],
            "edges": edges
        }
        
        trace.append({"step": "synthesis", "answer_length": len(answer)})
        
        return ChatResponse(
            message=answer,
            citations=[
                ChunkInfo(
                    chunk_id=c["chunk_id"],
                    object_id=c["object_id"],
                    title=c["title"],
                    section_type=c["section_type"],
                    distance=c["distance"],
                    content=""
                )
                for c in citations
            ],
            matched_objects=matched_objects,
            graph_data=graph_data,
            trace=trace
        )
