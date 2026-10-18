"""
BigQuery client for SAP Customizing RAG application.
Handles all BigQuery queries against the ingested corpus tables.
"""
import logging
from typing import Any, Dict, List, Optional

from google.cloud import bigquery
from google.oauth2 import service_account

from backend.config import settings, get_gcp_credentials_dict

logger = logging.getLogger(__name__)


class BigQueryClient:
    """
    Client for interacting with BigQuery.
    Reads the corpus tables created by the ingestion notebook.
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

    def _clean_tables_with_corpus(self, scope: str) -> List[tuple]:
        """Clean-table names paired with their corpus label for a scope."""
        if scope == "nova":
            return [(settings.nova_clean_table, "nova")]
        if scope == "standard":
            return [(settings.standard_clean_table, "standard")]
        return [
            (settings.standard_clean_table, "standard"),
            (settings.nova_clean_table, "nova"),
        ]

    def _union_with_corpus(self, tables: List[tuple], columns: str) -> str:
        """UNION ALL subquery with a corpus label per table."""
        return " UNION ALL ".join(
            f"SELECT {columns}, '{corpus}' AS corpus "
            f"FROM `{settings.gcp_project}.{self.dataset_id}.{t}`"
            for t, corpus in tables
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
            # Oversample so the join can drop non-embedded chunks and still fill top_k
            bigquery.ScalarQueryParameter("oversample", "INT64", top_k * 5),
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
                c.content_clean AS content,
                c.corpus
            FROM (
                SELECT 
                    chunk_id,
                    ML.DISTANCE(embedding, @q_vec) AS distance
                FROM ({self._union(self._embed_tables(scope), "chunk_id, embedding")})
                ORDER BY distance
                LIMIT @oversample
            ) AS e
            JOIN ({self._union_with_corpus(self._clean_tables_with_corpus(scope), "chunk_id, object_id, title, section_type, content_clean, embed")}) AS c
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
        # Get the object's references aggregated across ALL of its chunks —
        # refs are distributed per section (PRECONDITIONS, ACTIVITY, ...), so
        # any single row would carry only a subset
        sql = f"""
            SELECT r AS ref
            FROM ({self._union(self._clean_tables(scope), "object_id, element_refs")}) AS c,
                 UNNEST(c.element_refs) AS r
            WHERE c.object_id = @object_id
            GROUP BY 1
        """
        
        params = [bigquery.ScalarQueryParameter("object_id", "STRING", object_id)]
        results = self.query(sql, params)
        
        if not results:
            return {"nodes": [], "edges": []}
        
        refs = [row["ref"] for row in results]
        
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
    
    def get_related_objects_batch(self, object_ids: List[str], scope: str = "both") -> Dict[str, Dict[str, Any]]:
        """
        Graph data (nodes and edges) for several root objects in a single query pair.
        Returns {object_id: {"nodes": [...], "edges": [...]}}.
        """
        roots = list(dict.fromkeys(object_ids))
        if not roots:
            return {}
        
        sql = f"""
            SELECT c.object_id AS root, r AS ref
            FROM ({self._union(self._clean_tables(scope), "object_id, element_refs")}) AS c,
                 UNNEST(c.element_refs) AS r
            WHERE c.object_id IN UNNEST(@roots)
            GROUP BY 1, 2
        """
        params = [bigquery.ArrayQueryParameter("roots", "STRING", roots)]
        rows = self.query(sql, params)
        
        refs_by_root: Dict[str, set] = {}
        all_targets: set = set()
        for row in rows:
            if row["ref"].startswith("activity:"):
                target = row["ref"].replace("activity:", "")
                refs_by_root.setdefault(row["root"], set()).add(target)
                all_targets.add(target)
        
        titles: Dict[str, str] = {}
        title_ids = list(all_targets | set(roots))
        sql = f"""
            SELECT object_id, title
            FROM ({self._union(self._clean_tables(scope), "object_id, title")})
            WHERE object_id IN UNNEST(@ids)
            GROUP BY object_id, title
        """
        params = [bigquery.ArrayQueryParameter("ids", "STRING", title_ids)]
        for row in self.query(sql, params):
            titles[row["object_id"]] = row["title"]
        
        result = {}
        for oid in roots:
            nodes = [{"id": oid, "title": titles.get(oid, oid)}]
            edges = []
            for target in refs_by_root.get(oid, set()):
                nodes.append({"id": target, "title": titles.get(target, target)})
                edges.append({"source": oid, "target": target, "type": "activity"})
            result[oid] = {"nodes": nodes, "edges": edges}
        return result
    
    def get_object_infos_batch(self, object_ids: List[str], scope: str = "both") -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Object info (title + sections) for several objects in a single query.
        Returns {object_id: info-or-None} in the same key order as object_ids.
        """
        ids = list(dict.fromkeys(object_ids))
        if not ids:
            return {}
        
        sql = f"""
            SELECT object_id, title, section_type, content_clean AS content, corpus
            FROM ({self._union_with_corpus(self._clean_tables_with_corpus(scope), "object_id, title, section_type, content_clean")})
            WHERE object_id IN UNNEST(@ids)
        """
        params = [bigquery.ArrayQueryParameter("ids", "STRING", ids)]
        rows = self.query(sql, params)
        
        infos: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            info = infos.setdefault(row["object_id"], {"object_id": row["object_id"], "title": row["title"], "corpus": row["corpus"], "sections": {}})
            if row["section_type"] in info["sections"]:
                info["sections"][row["section_type"]] += "\n\n" + row["content"]
            else:
                info["sections"][row["section_type"]] = row["content"]
        return {oid: infos.get(oid) for oid in ids}
