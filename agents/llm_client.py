"""LLM client for interacting with language models."""
import json
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from config import settings
from groq import Groq

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM client supporting multiple providers."""
    
    def __init__(self):
        """Initialize LLM client."""
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url
        
        if self.provider == "openai":
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        elif self.provider == "groq":
            # Groq client automatically appends /openai/v1/chat/completions
            # If base_url includes /openai/v1, it will double to /openai/v1/openai/v1
            # Solution: For Groq, always use default (don't pass base_url) unless it's a custom endpoint
            
            if self.base_url:
                base_url_lower = self.base_url.lower().rstrip('/')
                
                # Ignore OpenAI URLs
                if "api.openai.com" in base_url_lower:
                    logger.warning(
                        f"LLM_BASE_URL is set to OpenAI URL ({self.base_url}) but provider is Groq. "
                        f"Ignoring base_url and using Groq's default endpoint."
                    )
                    self.client = Groq(api_key=self.api_key)
                # If base_url includes /openai/v1, strip it (Groq SDK adds this itself)
                elif "/openai/v1" in base_url_lower:
                    # Extract just the domain (e.g., https://api.groq.com)
                    normalized_url = base_url_lower.split("/openai/v1")[0].rstrip('/')
                    logger.info(
                        f"Stripping /openai/v1 from Groq base_url. Using: {normalized_url}"
                    )
                    self.client = Groq(api_key=self.api_key, base_url=normalized_url)
                elif "api.groq.com" in base_url_lower:
                    # Already just the domain, use as-is
                    self.client = Groq(api_key=self.api_key, base_url=self.base_url)
                else:
                    # Custom endpoint, try it as-is
                    logger.warning(
                        f"Using custom base_url for Groq: {self.base_url}. "
                        f"This may cause issues if it includes /openai/v1."
                    )
                    self.client = Groq(api_key=self.api_key, base_url=self.base_url)
            else:
                # No base_url set, use Groq's default (recommended)
                self.client = Groq(api_key=self.api_key)
        else:
            # For other providers (Ollama, etc.), use OpenAI-compatible interface
            self.client = OpenAI(
                api_key=self.api_key or "not-needed",
                base_url=self.base_url
            )
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate text using LLM.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            response_format: Optional response format (e.g., {"type": "json_object"})
            temperature: Optional temperature override
        
        Returns:
            Generated text
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temp,
            }
            
            # Only add response_format for OpenAI; Groq may ignore it
            if response_format and self.provider == "openai":
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text with LLM: {e}")
            raise
    
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            schema: Optional JSON schema
            
        Returns:
            Parsed JSON dict
        """
        # For Groq, emphasize JSON-only in prompt; for OpenAI, use response_format
        if self.provider == "groq":
            # Enhance system prompt to ensure JSON-only response
            enhanced_prompt = system_prompt + "\n\nIMPORTANT: Respond with a single JSON object only. Do not include any text before or after the JSON. Return only valid JSON."
            response_format = None
        else:
            enhanced_prompt = system_prompt
            response_format = {"type": "json_object"}
            if schema:
                # For models supporting JSON schema
                response_format = {"type": "json_object", "schema": schema}
        
        response = self.generate(enhanced_prompt, user_prompt, response_format=response_format)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed, attempting fallback extraction: {e}")
            logger.debug(f"Raw response (first 500 chars): {response[:500]}")
            
            # Fallback: extract first JSON object from response
            json_str = self._extract_json_from_text(response)
            if json_str:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"Could not parse JSON from response: {response[:500]}")
            raise
    
    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract first JSON object from text using brace matching.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            Extracted JSON string or None
        """
        # Find first {
        start_idx = text.find('{')
        if start_idx == -1:
            return None
        
        # Count braces to find matching }
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
        
        return None