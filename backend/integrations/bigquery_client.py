"""
BigQuery client for SAP Fit-Gap RAG application.
Handles all BigQuery operations including table creation and queries.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from google.cloud import bigquery
from google.oauth2 import service_account

from backend.config import settings, get_gcp_credentials_dict

logger = logging.getLogger(__name__)


class BigQueryClient:
    """
    Client for interacting with BigQuery.
    Automatically creates required tables if they don't exist.
    """
    
    def __init__(self):
        """Initialize the BigQuery client."""
        credentials_dict = get_gcp_credentials_dict()
        
        if credentials_dict:
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self.client = bigquery.Client(
                project=settings.gcp_project,
                credentials=self.credentials
            )
        else:
            # Use Application Default Credentials
            self.client = bigquery.Client(project=settings.gcp_project)
        
        self.dataset_id = settings.bq_dataset
        self._ensure_dataset()
        self._ensure_tables()
    
    def _ensure_dataset(self):
        """Ensure the dataset exists."""
        dataset_ref = self.client.dataset(self.dataset_id)
        try:
            dataset = self.client.get_dataset(dataset_ref)
            logger.info(f"Dataset {self.dataset_id} exists in location {dataset.location}")
        except Exception as e:
            logger.warning(f"Dataset {self.dataset_id} not found: {e}")
            try:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "us-central1"  # Use explicit location
                self.client.create_dataset(dataset, timeout=30)
                logger.info(f"Created dataset {self.dataset_id} in us-central1")
            except Exception as e2:
                logger.warning(f"Could not create dataset {self.dataset_id}: {e2}")
                # Dataset may already exist or we don't have permissions
                # Continue without failing - tables will be created on-demand
    
    def _ensure_tables(self):
        """Create required tables if they don't exist."""
        tables = [
            ("sessions", self._create_sessions_table_sql()),
            ("requirements", self._create_requirements_table_sql()),
            ("matches", self._create_matches_table_sql()),
            ("decisions", self._create_decisions_table_sql()),
        ]
        
        for table_name, sql in tables:
            try:
                job = self.client.query(sql)
                job.result(timeout=30)
                logger.info(f"Created or verified table: {table_name}")
            except Exception as e:
                # Check if table already exists
                if "Already Exists" in str(e) or "already exists" in str(e).lower():
                    logger.info(f"Table {table_name} already exists")
                else:
                    logger.error(f"Failed to create table {table_name}: {e}")
                    # Try to create it anyway with IF NOT EXISTS
                    try:
                        if_table_sql = sql.replace("CREATE OR REPLACE TABLE", "CREATE TABLE IF NOT EXISTS")
                        job = self.client.query(if_table_sql)
                        job.result(timeout=30)
                        logger.info(f"Created table {table_name} with IF NOT EXISTS")
                    except Exception as e2:
                        logger.error(f"Still failed to create table {table_name}: {e2}")
                        raise
    
    def _create_sessions_table_sql(self) -> str:
        """SQL to create sessions table."""
        return f"""
            CREATE TABLE IF NOT EXISTS `{settings.gcp_project}.{self.dataset_id}.sessions` (
                session_id STRING NOT NULL,
                kind STRING NOT NULL,
                title STRING,
                created_at TIMESTAMP NOT NULL,
                status STRING NOT NULL,
                source_ref STRING,
                metadata JSON
            )
        """
    
    def _create_requirements_table_sql(self) -> str:
        """SQL to create requirements table."""
        return f"""
            CREATE TABLE IF NOT EXISTS `{settings.gcp_project}.{self.dataset_id}.requirements` (
                req_id STRING NOT NULL,
                session_id STRING NOT NULL,
                ref_in_doc STRING,
                text STRING NOT NULL,
                category STRING,
                page INT64,
                speaker STRING,
                created_at TIMESTAMP NOT NULL
            )
        """
    
    def _create_matches_table_sql(self) -> str:
        """SQL to create matches table."""
        return f"""
            CREATE TABLE IF NOT EXISTS `{settings.gcp_project}.{self.dataset_id}.matches` (
                req_id STRING NOT NULL,
                session_id STRING NOT NULL,
                object_id STRING NOT NULL,
                distance FLOAT64 NOT NULL,
                verdict STRING NOT NULL,
                rationale STRING NOT NULL,
                model STRING NOT NULL,
                matched_objects ARRAY<STRING>,
                created_at TIMESTAMP NOT NULL
            )
        """
    
    def _create_decisions_table_sql(self) -> str:
        """SQL to create decisions table."""
        return f"""
            CREATE TABLE IF NOT EXISTS `{settings.gcp_project}.{self.dataset_id}.decisions` (
                decision_id STRING NOT NULL,
                session_id STRING NOT NULL,
                req_id STRING,
                question STRING NOT NULL,
                options ARRAY<STRING>,
                status STRING NOT NULL,
                answer STRING,
                source STRING NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """
    
    def get_table_ref(self, table_name: str) -> str:
        """Get fully qualified table reference."""
        return f"{settings.gcp_project}.{self.dataset_id}.{table_name}"
    
    def query(self, sql: str, params: Optional[List[bigquery.ScalarQueryParameter]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as dictionaries."""
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = params
        
        query_job = self.client.query(sql, job_config=job_config)
        results = query_job.result()
        
        return [dict(row) for row in results]
    
    def execute(self, sql: str, params: Optional[List[bigquery.ScalarQueryParameter]] = None) -> None:
        """Execute a non-query SQL statement (INSERT, UPDATE, DELETE)."""
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = params
        
        job = self.client.query(sql, job_config=job_config)
        job.result()
    
    # -------------------------------------------------------------------------
    # Retrieval Methods
    # -------------------------------------------------------------------------
    
    # ------------------------------------------------------------------
    # Corpus scope: standard (SAP) | nova (company standard) | both
    # ------------------------------------------------------------------
    VALID_SCOPES = ("standard", "nova", "both")

    def _clean_tables(self, scope: str) -> List[str]:
        """Clean-table names for a corpus scope."""
        if scope == "nova":
            return [settings.nova_clean_table]
        if scope == "standard":
            return [settings.standard_clean_table]
        return [settings.standard_clean_table, settings.nova_clean_table]

    def _embed_tables(self, scope: str) -> List[str]:
        """Embedding-table names for a corpus scope."""
        if scope == "nova":
            return [settings.nova_embeddings_table]
        if scope == "standard":
            return [settings.standard_embeddings_table]
        return [settings.standard_embeddings_table, settings.nova_embeddings_table]

    def _union(self, tables: List[str], columns: str) -> str:
        """UNION ALL subquery over the given corpus tables."""
        return " UNION ALL ".join(
            f"SELECT {columns} FROM `{settings.gcp_project}.{self.dataset_id}.{t}`"
            for t in tables
        )

    def retrieve_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 8,
        section_filter: Optional[str] = None,
        scope: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar chunks from the corpus using vector similarity.
        
        Args:
            query_embedding: The embedding vector for the query
            top_k: Number of results to return
            section_filter: Optional filter for section_type
        
        Returns:
            List of chunk information with similarity scores
        """
        params = [
            bigquery.ArrayQueryParameter("q_vec", "FLOAT64", query_embedding),
            bigquery.ScalarQueryParameter("k", "INT64", top_k),
        ]
        
        section_where = ""
        if section_filter:
            section_where = "AND c.section_type = @section_filter"
            params.append(bigquery.ScalarQueryParameter("section_filter", "STRING", section_filter))
        
        sql = f"""
            SELECT 
                e.chunk_id,
                c.object_id,
                c.title,
                c.section_type,
                distance,
                c.content_clean AS content
            FROM (
                SELECT 
                    chunk_id,
                    ML.DISTANCE(embedding, @q_vec) AS distance
                FROM ({self._union(self._embed_tables(scope), "chunk_id, embedding")})
            ) AS e
            JOIN ({self._union(self._clean_tables(scope), "chunk_id, object_id, title, section_type, content_clean, embed")}) AS c
                ON c.chunk_id = e.chunk_id
            WHERE c.embed = TRUE
            {section_where}
            ORDER BY distance
            LIMIT @k
        """
        
        return self.query(sql, params)
    
    def get_object_info(self, object_id: str, scope: str = "both") -> Optional[Dict[str, Any]]:
        """
        Get full information for a specific SAP object.
        
        Args:
            object_id: The SAP object ID
        
        Returns:
            Object information including all sections and references
        """
        sql = f"""
            SELECT 
                object_id,
                title,
                section_type,
                content_clean AS content,
                element_refs
            FROM ({self._union(self._clean_tables(scope), "object_id, title, section_type, content_clean, element_refs")})
            WHERE object_id = @object_id
            ORDER BY 
                CASE section_type
                    WHEN 'USE' THEN 1
                    WHEN 'SHORTTEXT' THEN 2
                    WHEN 'PRECONDITIONS' THEN 3
                    WHEN 'STANDARD_SETUP' THEN 4
                    WHEN 'ACTIVITY' THEN 5
                    WHEN 'EXAMPLE' THEN 6
                    WHEN 'ADDITIONAL_HINTS' THEN 7
                    WHEN 'SEE_ALSO' THEN 8
                    WHEN 'FURTHER_SOURCES_OF_INF' THEN 9
                    ELSE 100
                END
        """
        
        params = [bigquery.ScalarQueryParameter("object_id", "STRING", object_id)]
        results = self.query(sql, params)
        
        if not results:
            return None
        
        # Group by object and aggregate sections
        object_info: Dict[str, Any] = {
            "object_id": object_id,
            "title": results[0]["title"],
            "sections": {},
            "element_refs": [],
        }
        
        for row in results:
            section_type = row["section_type"]
            if section_type not in object_info["sections"]:
                object_info["sections"][section_type] = row["content"]
            else:
                # Append to existing section
                object_info["sections"][section_type] += "\n\n" + row["content"]
            
            if row["element_refs"]:
                object_info["element_refs"].extend(row["element_refs"])
        
        # Deduplicate references
        object_info["element_refs"] = list(set(object_info["element_refs"]))
        
        return object_info
    
    def get_related_objects(self, object_id: str, depth: int = 1, scope: str = "both") -> Dict[str, Any]:
        """
        Get objects related to the given object via element_refs.
        
        Args:
            object_id: The source object ID
            depth: How many hops to follow (1 = direct neighbors)
        
        Returns:
            Graph data with nodes and edges
        """
        # Get the object's references
        sql = f"""
            SELECT element_refs
            FROM ({self._union(self._clean_tables(scope), "element_refs")})
            WHERE object_id = @object_id
            LIMIT 1
        """
        
        params = [bigquery.ScalarQueryParameter("object_id", "STRING", object_id)]
        results = self.query(sql, params)
        
        if not results or not results[0]["element_refs"]:
            return {"nodes": [], "edges": []}
        
        refs = results[0]["element_refs"]
        
        # Extract activity references
        activity_refs = [r.replace("activity:", "") for r in refs if r.startswith("activity:")]
        
        if not activity_refs:
            return {"nodes": [], "edges": []}
        
        # Get info for related objects
        placeholders = ", ".join(["?" for _ in activity_refs])
        sql = f"""
            SELECT object_id, title
            FROM ({self._union(self._clean_tables(scope), "object_id, title")})
            WHERE object_id IN UNNEST(@activity_refs)
            GROUP BY object_id, title
        """
        
        params = [bigquery.ArrayQueryParameter("activity_refs", "STRING", activity_refs)]
        related = self.query(sql, params)
        
        nodes = [
            {"id": object_id, "title": self.get_object_info(object_id)["title"] if self.get_object_info(object_id) else object_id}
        ]
        edges = []
        
        for ref in related:
            ref_id = ref["object_id"]
            nodes.append({"id": ref_id, "title": ref["title"]})
            edges.append({"source": object_id, "target": ref_id, "type": "activity"})
        
        return {"nodes": nodes, "edges": edges}
    
    # -------------------------------------------------------------------------
    # Session Management Methods
    # -------------------------------------------------------------------------
    
    def create_session(self, session_id: str, kind: str, title: str, source_ref: Optional[str] = None) -> None:
        """Create a new session record."""
        from datetime import datetime
        
        sql = f"""
            INSERT INTO `{settings.gcp_project}.{self.dataset_id}.sessions`
            (session_id, kind, title, created_at, status, source_ref, metadata)
            VALUES (@session_id, @kind, @title, @created_at, @status, @source_ref, @metadata)
        """
        
        params = [
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("kind", "STRING", kind),
            bigquery.ScalarQueryParameter("title", "STRING", title),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", datetime.utcnow().isoformat()),
            bigquery.ScalarQueryParameter("status", "STRING", "pending"),
            bigquery.ScalarQueryParameter("source_ref", "STRING", source_ref or ""),
            bigquery.ScalarQueryParameter("metadata", "JSON", json.dumps({})),
        ]
        
        self.execute(sql, params)
    
    def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        sql = f"""
            UPDATE `{settings.gcp_project}.{self.dataset_id}.sessions`
            SET status = @status
            WHERE session_id = @session_id
        """
        
        params = [
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("status", "STRING", status),
        ]
        
        self.execute(sql, params)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.sessions`
            WHERE session_id = @session_id
        """
        
        params = [bigquery.ScalarQueryParameter("session_id", "STRING", session_id)]
        results = self.query(sql, params)
        
        if not results:
            return None
        
        session = results[0]
        # Ensure metadata is a dict, not None or string
        if session.get('metadata') is None:
            session['metadata'] = {}
        elif isinstance(session.get('metadata'), str):
            try:
                session['metadata'] = json.loads(session['metadata'])
            except (json.JSONDecodeError, TypeError):
                session['metadata'] = {}
        
        return session
    
    def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List recent sessions."""
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.sessions`
            ORDER BY created_at DESC
            LIMIT @limit
        """
        
        params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
        sessions = self.query(sql, params)
        # Ensure metadata is a dict, not None or string for all sessions
        for session in sessions:
            if session.get('metadata') is None:
                session['metadata'] = {}
            elif isinstance(session.get('metadata'), str):
                try:
                    session['metadata'] = json.loads(session['metadata'])
                except (json.JSONDecodeError, TypeError):
                    session['metadata'] = {}
        return sessions
    
    # -------------------------------------------------------------------------
    # Requirement, Match, and Decision Methods
    # -------------------------------------------------------------------------
    
    def create_requirement(self, req_id: str, session_id: str, text: str, **kwargs) -> None:
        """Create a new requirement."""
        from datetime import datetime
        
        sql = f"""
            INSERT INTO `{settings.gcp_project}.{self.dataset_id}.requirements`
            (req_id, session_id, text, created_at, ref_in_doc, category, page, speaker)
            VALUES (@req_id, @session_id, @text, @created_at, @ref_in_doc, @category, @page, @speaker)
        """
        
        params = [
            bigquery.ScalarQueryParameter("req_id", "STRING", req_id),
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("text", "STRING", text),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", datetime.utcnow().isoformat()),
            bigquery.ScalarQueryParameter("ref_in_doc", "STRING", kwargs.get("ref_in_doc", "")),
            bigquery.ScalarQueryParameter("category", "STRING", kwargs.get("category", "")),
            bigquery.ScalarQueryParameter("page", "INT64", kwargs.get("page", 0)),
            bigquery.ScalarQueryParameter("speaker", "STRING", kwargs.get("speaker", "")),
        ]
        
        self.execute(sql, params)
    
    def get_requirements(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all requirements for a session."""
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.requirements`
            WHERE session_id = @session_id
            ORDER BY created_at
        """
        
        params = [bigquery.ScalarQueryParameter("session_id", "STRING", session_id)]
        return self.query(sql, params)
    
    def create_match(self, req_id: str, session_id: str, object_id: str, distance: float, 
                   verdict: str, rationale: str, model: str, matched_objects: List[str]) -> None:
        """Create a new match record."""
        from datetime import datetime
        
        sql = f"""
            INSERT INTO `{settings.gcp_project}.{self.dataset_id}.matches`
            (req_id, session_id, object_id, distance, verdict, rationale, model, matched_objects, created_at)
            VALUES (@req_id, @session_id, @object_id, @distance, @verdict, @rationale, @model, @matched_objects, @created_at)
        """
        
        params = [
            bigquery.ScalarQueryParameter("req_id", "STRING", req_id),
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("object_id", "STRING", object_id),
            bigquery.ScalarQueryParameter("distance", "FLOAT64", distance),
            bigquery.ScalarQueryParameter("verdict", "STRING", verdict),
            bigquery.ScalarQueryParameter("rationale", "STRING", rationale),
            bigquery.ScalarQueryParameter("model", "STRING", model),
            bigquery.ArrayQueryParameter("matched_objects", "STRING", matched_objects),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", datetime.utcnow().isoformat()),
        ]
        
        self.execute(sql, params)
    
    def get_matches(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all matches for a session."""
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.matches`
            WHERE session_id = @session_id
            ORDER BY created_at
        """
        
        params = [bigquery.ScalarQueryParameter("session_id", "STRING", session_id)]
        return self.query(sql, params)
    
    def create_decision(self, decision_id: str, session_id: str, question: str, 
                       req_id: Optional[str] = None, options: Optional[List[str]] = None,
                       status: str = "open", answer: Optional[str] = None, 
                       source: str = "manual") -> None:
        """Create a new decision."""
        from datetime import datetime
        
        sql = f"""
            INSERT INTO `{settings.gcp_project}.{self.dataset_id}.decisions`
            (decision_id, session_id, req_id, question, options, status, answer, source, created_at)
            VALUES (@decision_id, @session_id, @req_id, @question, @options, @status, @answer, @source, @created_at)
        """
        
        params = [
            bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id),
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("req_id", "STRING", req_id or ""),
            bigquery.ScalarQueryParameter("question", "STRING", question),
            bigquery.ArrayQueryParameter("options", "STRING", options or []),
            bigquery.ScalarQueryParameter("status", "STRING", status),
            bigquery.ScalarQueryParameter("answer", "STRING", answer or ""),
            bigquery.ScalarQueryParameter("source", "STRING", source),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", datetime.utcnow().isoformat()),
        ]
        
        self.execute(sql, params)
    
    def get_decisions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all decisions for a session."""
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.decisions`
            WHERE session_id = @session_id
            ORDER BY created_at
        """
        
        params = [bigquery.ScalarQueryParameter("session_id", "STRING", session_id)]
        return self.query(sql, params)
    
    def update_decision(self, decision_id: str, status: Optional[str] = None, 
                       answer: Optional[str] = None) -> None:
        """Update a decision."""
        updates = []
        params = []
        
        if status:
            updates.append("status = @status")
            params.append(bigquery.ScalarQueryParameter("status", "STRING", status))
        
        if answer:
            updates.append("answer = @answer")
            params.append(bigquery.ScalarQueryParameter("answer", "STRING", answer))
        
        if not updates:
            return
        
        sql = f"""
            UPDATE `{settings.gcp_project}.{self.dataset_id}.decisions`
            SET {', '.join(updates)}
            WHERE decision_id = @decision_id
        """
        
        params.append(bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id))
        self.execute(sql, params)
    
    def get_open_decisions(self, project_scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open decisions, optionally filtered by project scope.
        For v1, project_scope is not used (all sessions).
        """
        sql = f"""
            SELECT *
            FROM `{settings.gcp_project}.{self.dataset_id}.decisions`
            WHERE status = 'open'
            ORDER BY created_at
        """
        
        return self.query(sql)
    
    def clear_all_sessions(self) -> Dict[str, int]:
        """
        Clear all sessions and their related data (requirements, matches, decisions).
        Returns a dict with counts of deleted records.
        """
        counts = {"sessions": 0, "requirements": 0, "matches": 0, "decisions": 0}
        
        # Delete decisions
        sql = f"""
            SELECT COUNT(*) as count
            FROM `{settings.gcp_project}.{self.dataset_id}.decisions`
        """
        result = self.query(sql)
        if result:
            counts["decisions"] = result[0]["count"]
        
        sql = f"DELETE FROM `{settings.gcp_project}.{self.dataset_id}.decisions` WHERE TRUE"
        self.execute(sql)
        
        # Delete matches
        sql = f"""
            SELECT COUNT(*) as count
            FROM `{settings.gcp_project}.{self.dataset_id}.matches`
        """
        result = self.query(sql)
        if result:
            counts["matches"] = result[0]["count"]
        
        sql = f"DELETE FROM `{settings.gcp_project}.{self.dataset_id}.matches` WHERE TRUE"
        self.execute(sql)
        
        # Delete requirements
        sql = f"""
            SELECT COUNT(*) as count
            FROM `{settings.gcp_project}.{self.dataset_id}.requirements`
        """
        result = self.query(sql)
        if result:
            counts["requirements"] = result[0]["count"]
        
        sql = f"DELETE FROM `{settings.gcp_project}.{self.dataset_id}.requirements` WHERE TRUE"
        self.execute(sql)
        
        # Delete sessions
        sql = f"""
            SELECT COUNT(*) as count
            FROM `{settings.gcp_project}.{self.dataset_id}.sessions`
        """
        result = self.query(sql)
        if result:
            counts["sessions"] = result[0]["count"]
        
        sql = f"DELETE FROM `{settings.gcp_project}.{self.dataset_id}.sessions` WHERE TRUE"
        self.execute(sql)
        
        logger.info(f"Cleared {counts['sessions']} sessions, {counts['requirements']} requirements, {counts['matches']} matches, {counts['decisions']} decisions")
        return counts
