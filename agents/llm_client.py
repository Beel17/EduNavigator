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
            self.client = Groq(
                api_key=self.api_key,
                base_url=self.base_url
            )
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
            
            if response_format:
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
        response_format = {"type": "json_object"}
        if schema:
            # For models supporting JSON schema
            response_format = {"type": "json_object", "schema": schema}
        
        response = self.generate(system_prompt, user_prompt, response_format=response_format)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response: {response}")
            raise

