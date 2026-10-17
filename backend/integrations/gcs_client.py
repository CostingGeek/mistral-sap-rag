"""
Google Cloud Storage client for file uploads and downloads.
"""
import logging
from pathlib import Path
from typing import BinaryIO, Optional, Union

from google.cloud import storage
from google.oauth2 import service_account

from backend.config import settings, get_gcp_credentials_dict

logger = logging.getLogger(__name__)


class GCSClient:
    """
    Client for interacting with Google Cloud Storage.
    """
    
    def __init__(self):
        """Initialize the GCS client."""
        credentials_dict = get_gcp_credentials_dict()
        
        if credentials_dict:
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/devstorage.read_write"]
            )
            self.client = storage.Client(
                project=settings.gcp_project,
                credentials=self.credentials
            )
        else:
            self.client = storage.Client(project=settings.gcp_project)
        
        self.bucket_name = settings.bucket_name or ""
        self.bucket = self.client.bucket(self.bucket_name) if self.bucket_name else None
    
    def upload_file(
        self,
        source_path: Union[str, Path, BinaryIO],
        destination_blob_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to GCS.
        
        Args:
            source_path: Path to the source file or file-like object
            destination_blob_name: Destination blob name in GCS
            content_type: Optional content type
        
        Returns:
            The GCS URI of the uploaded file
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured, skipping upload")
            return ""
        blob = self.bucket.blob(destination_blob_name)
        
        if isinstance(source_path, (str, Path)):
            blob.upload_from_filename(str(source_path), content_type=content_type)
        else:
            blob.upload_from_file(source_path, content_type=content_type)
        
        logger.info(f"Uploaded {destination_blob_name} to GCS")
        return f"gs://{self.bucket_name}/{destination_blob_name}"
    
    def upload_bytes(
        self,
        data: bytes,
        destination_blob_name: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload bytes to GCS.
        
        Args:
            data: Bytes to upload
            destination_blob_name: Destination blob name in GCS
            content_type: Optional content type
        
        Returns:
            The GCS URI of the uploaded file
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured, skipping upload")
            return ""
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_string(data, content_type=content_type)
        
        logger.info(f"Uploaded bytes to {destination_blob_name}")
        return f"gs://{self.bucket_name}/{destination_blob_name}"
    
    def download_file(
        self,
        blob_name: str,
        destination_path: Union[str, Path, BinaryIO]
    ) -> None:
        """
        Download a file from GCS.
        
        Args:
            blob_name: Name of the blob to download
            destination_path: Destination path or file-like object
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured, skipping download")
            return
        blob = self.bucket.blob(blob_name)
        
        if isinstance(destination_path, (str, Path)):
            blob.download_to_filename(str(destination_path))
        else:
            blob.download_to_file(destination_path)
        
        logger.info(f"Downloaded {blob_name} from GCS")
    
    def download_bytes(self, blob_name: str) -> bytes:
        """
        Download a file from GCS as bytes.
        
        Args:
            blob_name: Name of the blob to download
        
        Returns:
            File content as bytes
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured, skipping download")
            return b""
        blob = self.bucket.blob(blob_name)
        return blob.download_as_bytes()
    
    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in GCS.
        
        Args:
            blob_name: Name of the blob
        
        Returns:
            True if the blob exists
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured")
            return False
        blob = self.bucket.blob(blob_name)
        return blob.exists()
    
    def delete_blob(self, blob_name: str) -> None:
        """
        Delete a blob from GCS.
        
        Args:
            blob_name: Name of the blob to delete
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured, skipping delete")
            return
        blob = self.bucket.blob(blob_name)
        blob.delete()
        logger.info(f"Deleted {blob_name} from GCS")
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Get the GCS URI for a blob.
        
        Args:
            blob_name: Name of the blob
        
        Returns:
            The GCS URI
        """
        if not self.bucket_name:
            logger.warning("GCS bucket not configured")
            return ""
        return f"gs://{self.bucket_name}/{blob_name}"
    
    def list_blobs(self, prefix: str = "") -> list:
        """
        List blobs with a given prefix.
        
        Args:
            prefix: Prefix to filter blobs
        
        Returns:
            List of blob names
        """
        if not self.bucket:
            logger.warning("GCS bucket not configured")
            return []
        blobs = self.client.list_blobs(self.bucket, prefix=prefix)
        return [blob.name for blob in blobs]
