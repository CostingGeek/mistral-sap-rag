"""
Mistral AI client for embeddings, chat, OCR, and ASR.
"""
import base64
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from backend.config import settings

logger = logging.getLogger(__name__)


class MistralClient:
    """
    Client for Mistral AI APIs.
    Handles embeddings, chat completion, OCR, and ASR (Voxtral).
    """
    
    BASE_URL = "https://api.mistral.ai/v1"
    
    def __init__(self):
        """Initialize the Mistral client."""
        self.api_key = settings.mistral_api_key.get_secret_value()
        self.base_url = settings.mistral_base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        self._rate_limit_delay = settings.mistral_rate_limit_delay
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        Make an HTTP request to Mistral API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: JSON payload
            files: Files for multipart upload
            stream: Whether to stream the response
            **kwargs: Additional arguments
        
        Returns:
            Response data or streaming generator
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(3):
            try:
                if files:
                    response = self.session.request(
                        method, url, files=files, timeout=120, **kwargs
                    )
                else:
                    response = self.session.request(
                        method, url, json=data, timeout=120, **kwargs
                    )
                
                if response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                if stream:
                    return response.iter_lines()
                else:
                    return response.json()
            
            except requests.exceptions.Timeout:
                if attempt < 2:
                    wait_time = 2 ** attempt
                    logger.warning(f"Timeout, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
            
            except Exception as e:
                if attempt < 2:
                    wait_time = 2 ** attempt
                    logger.warning(f"Error: {e}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
        
        raise RuntimeError("Should not reach here")
    
    # -------------------------------------------------------------------------
    # Embeddings
    # -------------------------------------------------------------------------
    
    def create_embedding(
        self,
        text: str,
        model: str = None
    ) -> List[float]:
        """
        Create an embedding for a single text.
        
        Args:
            text: Text to embed
            model: Model to use (default from settings)
        
        Returns:
            Embedding vector
        """
        model = model or settings.embed_model
        
        data = {
            "model": model,
            "input": text,
            "encoding_format": "float"
        }
        
        result = self._request("POST", "/embeddings", data)
        
        if "data" not in result or len(result["data"]) == 0:
            raise ValueError(f"No embedding data returned: {result}")
        
        return result["data"][0]["embedding"]
    
    def create_embeddings(
        self,
        texts: List[str],
        model: str = None,
        batch_size: int = 64
    ) -> List[List[float]]:
        """
        Create embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            model: Model to use
            batch_size: Number of texts per batch
        
        Returns:
            List of embedding vectors
        """
        model = model or settings.embed_model
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            data = {
                "model": model,
                "input": batch,
                "encoding_format": "float"
            }
            
            result = self._request("POST", "/embeddings", data)
            
            if "data" not in result:
                raise ValueError(f"No embedding data returned: {result}")
            
            batch_embeddings = [d["embedding"] for d in result["data"]]
            embeddings.extend(batch_embeddings)
            
            # Rate limiting
            if self._rate_limit_delay > 0 and i + batch_size < len(texts):
                time.sleep(self._rate_limit_delay)
        
        return embeddings
    
    # -------------------------------------------------------------------------
    # Chat Completion
    # -------------------------------------------------------------------------
    
    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Get chat completion from Mistral.
        
        Args:
            messages: List of message dictionaries
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            response_format: Optional response format (e.g., JSON mode)
            **kwargs: Additional arguments
        
        Returns:
            Completion response or streaming generator
        """
        model = model or settings.chat_model
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        if response_format:
            data["response_format"] = response_format
        
        data.update(kwargs)
        
        return self._request("POST", "/chat/completions", data, stream=stream)
    
    # -------------------------------------------------------------------------
    # OCR (Mistral OCR API)
    # -------------------------------------------------------------------------
    
    def ocr_document(
        self,
        file_path: Union[str, Path],
        language: str = "en"
    ) -> str:
        """
        Perform OCR on a document image or PDF.
        
        Args:
            file_path: Path to the file
            language: Language of the text
        
        Returns:
            Extracted text
        """
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        files = {
            "file": (Path(file_path).name, file_content, "application/pdf"),
        }
        
        data = {
            "language": language,
        }
        
        result = self._request("POST", "/ocr", data, files=files)
        
        if "text" in result:
            return result["text"]
        elif "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["text"]
        else:
            raise ValueError(f"Unexpected OCR response format: {result}")
    
    def ocr_document_bytes(
        self,
        file_content: bytes,
        file_name: str,
        language: str = "en"
    ) -> str:
        """
        Perform OCR on document bytes.
        
        Args:
            file_content: File content as bytes
            file_name: Name of the file
            language: Language of the text
        
        Returns:
            Extracted text
        """
        files = {
            "file": (file_name, file_content, "application/pdf"),
        }
        
        data = {
            "language": language,
        }
        
        result = self._request("POST", "/ocr", data, files=files)
        
        if "text" in result:
            return result["text"]
        elif "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["text"]
        else:
            raise ValueError(f"Unexpected OCR response format: {result}")
    
    # -------------------------------------------------------------------------
    # ASR (Voxtral Speech-to-Text)
    # -------------------------------------------------------------------------
    
    def transcribe_audio(
        self,
        file_path: Union[str, Path],
        language: str = "en",
        diarization: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Voxtral ASR.
        
        Args:
            file_path: Path to the audio file
            language: Language of the audio
            diarization: Whether to enable speaker diarization
        
        Returns:
            Transcription result with diarization if enabled
        """
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        files = {
            "file": (Path(file_path).name, file_content, "audio/mpeg"),
        }
        
        data = {
            "language": language,
            "diarization": diarization,
        }
        
        result = self._request("POST", "/audio/transcriptions", data, files=files)
        
        return result
    
    def transcribe_audio_bytes(
        self,
        file_content: bytes,
        file_name: str,
        language: str = "en",
        diarization: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio bytes using Voxtral ASR.
        
        Args:
            file_content: Audio content as bytes
            file_name: Name of the file
            language: Language of the audio
            diarization: Whether to enable speaker diarization
        
        Returns:
            Transcription result with diarization if enabled
        """
        files = {
            "file": (file_name, file_content, "audio/mpeg"),
        }
        
        data = {
            "language": language,
            "diarization": diarization,
        }
        
        result = self._request("POST", "/audio/transcriptions", data, files=files)
        
        return result
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    def extract_json_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: str = None,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Get a structured JSON response from Mistral.
        
        Args:
            prompt: The prompt to send
            schema: JSON schema for the response
            model: Model to use
            temperature: Sampling temperature (0 for deterministic)
        
        Returns:
            Parsed JSON response
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that returns valid JSON. Follow the schema exactly."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nReturn the response as valid JSON following this schema:\n{json.dumps(schema)}"
            }
        ]
        
        result = self.chat_completion(
            messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the content
                import re
                match = re.search(r'\{[^}]*\}', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise ValueError(f"Could not parse JSON from response: {content}")
        else:
            raise ValueError(f"Unexpected response format: {result}")
