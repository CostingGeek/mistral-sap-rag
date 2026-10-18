"""
Chat service for agentic retrieval and conversation.
"""
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
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
    
    def classify_intent(self, question: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """
        Classify the intent of a question.
        
        Args:
            question: The user's question
        
        Returns:
            Tuple of (intent classification, token usage or None)
        """
        prompt = f"""
Classify the following question and determine if it should be decomposed into sub-queries. Only decompose if the question genuinely spans separate topics; prefer a single query otherwise.

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
                model=settings.classify_model,
                schema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["simple", "multi_intent", "follow_up"]},
                        "query": {"type": "string"},
                        "sub_queries": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
            return result, self.mistral_client.pop_last_usage()
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, using simple query")
            return {"type": "simple", "query": question}, None
    
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
                content=row["content"],
                corpus=row.get("corpus")
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
            # One query for all roots' references, one for all new objects' info
            graphs = self.bq_client.get_related_objects_batch(list(object_ids), scope=scope)
            new_targets = set()
            for graph in graphs.values():
                for edge in graph["edges"]:
                    edges.append(edge)
                    if edge["target"] not in object_ids:
                        new_targets.add(edge["target"])
            
            if not new_targets:
                break
            
            infos = self.bq_client.get_object_infos_batch(list(new_targets), scope=scope)
            for obj_id, obj_info in infos.items():
                self._object_info_cache[f"{scope}:{obj_id}"] = obj_info
                if obj_info and obj_info.get("sections"):
                    # Create chunks for USE and SHORTTEXT sections
                    for section_type, content in obj_info["sections"].items():
                        if section_type in ["USE", "SHORTTEXT"]:
                            additional_chunks.append(
                                ChunkInfo(
                                    chunk_id=f"{obj_id}::{section_type}",
                                    object_id=obj_id,
                                    title=obj_info["title"],
                                    section_type=section_type,
                                    distance=0.0,  # Not applicable for graph-expanded chunks
                                    content=content,
                                    corpus=obj_info.get("corpus"),
                                    graph_expanded=True
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
    ) -> Tuple[str, List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Synthesize an answer from retrieved chunks.
        
        Args:
            query: The user's query
            chunks: Retrieved chunks with context
            history: Optional conversation history
        
        Returns:
            Tuple of (answer text, citations, token usage or None)
        """
        # Build the context from chunks
        context_parts = []
        corpus_labels = {"standard": "SAP standard", "nova": "Company standard"}
        for i, chunk in enumerate(chunks):
            corpus_label = corpus_labels.get(chunk.corpus) if chunk.corpus else None
            corpus_part = f", Corpus: {corpus_label}" if corpus_label else ""
            context_parts.append(
                f"Source {i+1} (Object: {chunk.object_id}, Section: {chunk.section_type}{corpus_part}, Distance: {chunk.distance:.4f}):\n"
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
- Cite sources using the format: [Source N] where N is the source number. Always include the square brackets, exactly as shown
- When a source is labeled with a corpus, make clear whether the guidance comes from the SAP standard or the company standard
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
                    "distance": chunk.distance,
                    "corpus": chunk.corpus,
                    "graph_expanded": chunk.graph_expanded,
                    "source_no": i + 1,
                })
        
        return answer, citations, self.mistral_client.pop_last_usage()
    
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
        
        t_start = time.perf_counter()

        # Step 1: Intent classification
        t = time.perf_counter()
        intent, intent_tokens = self.classify_intent(query)
        t_intent = time.perf_counter() - t
        trace = [{
            "step": "intent_classification",
            "result": intent,
            "duration_ms": round(t_intent * 1000),
            "tokens": intent_tokens,
        }]
        
        # Step 2: Generate queries
        if intent["type"] == "multi_intent":
            # Latency scales with sub-query count; cap the fan-out
            queries = intent["sub_queries"][:3]
            trace.append({"step": "query_decomposition", "queries": queries})
        else:
            queries = [intent.get("query", query)]
        
        # Step 3: Retrieve chunks for each query (sub-queries run in parallel)
        all_chunks = []
        t = time.perf_counter()
        per_query_k = max(3, top_k // len(queries))

        def _timed_retrieve(q: str):
            started = time.perf_counter()
            chunks = self.retrieve_chunks(q, top_k=per_query_k, scope=scope)
            # Embedding token usage for this sub-query (thread-local in MistralClient)
            tokens = self.mistral_client.pop_last_usage()
            return q, chunks, round((time.perf_counter() - started) * 1000), tokens
        
        with ThreadPoolExecutor(max_workers=min(4, len(queries))) as pool:
            for q, chunks, duration_ms, tokens in pool.map(_timed_retrieve, queries):
                all_chunks.extend(chunks)
                trace.append({
                    "step": "retrieval",
                    "query": q,
                    "chunk_count": len(chunks),
                    "duration_ms": duration_ms,
                    "tokens": tokens
                })
        t_retrieval = time.perf_counter() - t
        
        # Deduplicate chunks
        seen_chunk_ids = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)
        
        all_chunks = unique_chunks
        
        # Step 4: Graph expansion
        t = time.perf_counter()
        expanded_chunks, edges = self.expand_graph(all_chunks, hops=1, scope=scope)
        t_graph = time.perf_counter() - t
        trace.append({
            "step": "graph_expansion",
            "original_count": len(all_chunks),
            "expanded_count": len(expanded_chunks),
            "edge_count": len(edges),
            "duration_ms": round(t_graph * 1000)
        })
        
        # Step 5: Synthesize answer
        t = time.perf_counter()
        answer, citations, synthesis_tokens = self.synthesize_answer(
            query,
            expanded_chunks,
            history
        )
        t_synthesis = time.perf_counter() - t
        
        # Build matched objects
        matched_objects = list({c.object_id for c in expanded_chunks})
        
        # Build graph data
        graph_data = {
            "nodes": [{"id": c.object_id, "title": c.title} for c in expanded_chunks],
            "edges": edges
        }
        
        trace.append({
            "step": "synthesis",
            "answer_length": len(answer),
            "duration_ms": round(t_synthesis * 1000),
            "tokens": synthesis_tokens,
        })

        total = time.perf_counter() - t_start
        token_totals = {"prompt": 0, "completion": 0, "total": 0}
        for entry in trace:
            tokens = entry.get("tokens")
            if tokens:
                token_totals["prompt"] += tokens.get("prompt", 0) or 0
                token_totals["completion"] += tokens.get("completion", 0) or 0
        token_totals["total"] = token_totals["prompt"] + token_totals["completion"]
        trace.append({"step": "total", "duration_ms": round(total * 1000), "tokens": token_totals})
        logger.info(
            "chat timing: total=%.2fs intent=%.2fs retrieval=%.2fs graph=%.2fs synthesis=%.2fs "
            "(queries=%d, chunks=%d, tokens: %d in / %d out)",
            total, t_intent, t_retrieval, t_graph, t_synthesis, len(queries), len(expanded_chunks),
            token_totals["prompt"], token_totals["completion"],
        )
        
        return ChatResponse(
            message=answer,
            citations=[
                ChunkInfo(
                    chunk_id=c["chunk_id"],
                    object_id=c["object_id"],
                    title=c["title"],
                    section_type=c["section_type"],
                    distance=c["distance"],
                    content="",
                    corpus=c["corpus"],
                    graph_expanded=c["graph_expanded"],
                    source_no=c["source_no"],
                )
                for c in citations
            ],
            matched_objects=matched_objects,
            graph_data=graph_data,
            trace=trace
        )
