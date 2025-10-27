"""
LLM Model Module for Aviation RAG System.

This module provides a wrapper around Llama via Ollama for text generation.

Usage:
    from models.llm import LlamaModel

    llm = LlamaModel()
    response = llm.generate("Qual é a capital do Brasil?")
"""

import time
from typing import Dict, List, Optional

import ollama
from loguru import logger

from config import config


class LlamaModel:
    """
    Wrapper for Llama LLM via Ollama.

    This class provides a simple interface for text generation with
    configurable parameters and error handling.

    Attributes:
        model_name: Name of the Ollama model
        host: Ollama server URL
        default_options: Default generation options
    """

    def __init__(
        self,
        model_name: str = None,
        host: str = None,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None
    ):
        """
        Initialize Llama model.

        Args:
            model_name: Ollama model name (default from config)
            host: Ollama server URL (default from config)
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
        """
        self.model_name = model_name or config.OLLAMA_MODEL
        self.host = host or config.OLLAMA_HOST
        self.temperature = temperature or config.LLM_TEMPERATURE
        self.top_p = top_p or config.LLM_TOP_P
        self.max_tokens = max_tokens or config.LLM_MAX_TOKENS

        # Default generation options
        self.default_options = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_predict": self.max_tokens,
        }

        logger.info(f"Initializing LlamaModel: {self.model_name} @ {self.host}")

        # Test connection
        self._test_connection()

    def _test_connection(self) -> bool:
        """
        Test connection to Ollama server and model availability.

        Returns:
            bool: True if connection successful

        Raises:
            ConnectionError: If cannot connect to Ollama
            ValueError: If model not available
        """
        try:
            # List available models
            logger.debug("Testing Ollama connection...")
            models = ollama.list()

            # Check if our model is available
            available_models = [m["name"] for m in models.get("models", [])]

            if self.model_name not in available_models:
                logger.warning(
                    f"Model '{self.model_name}' not found in Ollama. "
                    f"Available models: {available_models}"
                )
                logger.warning(
                    f"You may need to pull the model: "
                    f"ollama pull {self.model_name}"
                )
                # Don't raise error, just warn - model might be pullable
            else:
                logger.success(
                    f"Ollama connection successful. Model '{self.model_name}' available."
                )

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.error(
                f"Please ensure Ollama is running at {self.host} and "
                f"the model is installed: ollama pull {self.model_name}"
            )
            raise ConnectionError(f"Cannot connect to Ollama: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            system_prompt: Optional system message (e.g., role instructions)
            temperature: Override default temperature
            top_p: Override default top_p
            max_tokens: Override default max_tokens
            stream: Stream response (not implemented yet)

        Returns:
            Generated text

        Example:
            >>> llm = LlamaModel()
            >>> response = llm.generate(
            ...     "Explique o que é RAG",
            ...     system_prompt="Você é um assistente especializado em IA"
            ... )
        """
        # Build options
        options = self.default_options.copy()
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        logger.debug(
            f"Generating text (model={self.model_name}, "
            f"temp={options['temperature']}, "
            f"max_tokens={options['num_predict']})"
        )

        start_time = time.time()

        try:
            # Build messages
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Generate
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options=options,
                stream=stream
            )

            # Extract text
            generated_text = response["message"]["content"]

            generation_time = time.time() - start_time
            tokens_generated = len(generated_text.split())  # Rough estimate
            tokens_per_second = tokens_generated / generation_time if generation_time > 0 else 0

            logger.debug(
                f"Generated {tokens_generated} tokens in {generation_time:.2f}s "
                f"({tokens_per_second:.1f} tokens/s)"
            )

            return generated_text

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise

    def generate_with_context(
        self,
        query: str,
        context_documents: List[Dict],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text with retrieved context documents (RAG).

        Args:
            query: User query
            context_documents: List of context documents with text and metadata
            system_prompt: Optional system prompt
            **kwargs: Additional arguments for generate()

        Returns:
            Generated response

        Example:
            >>> llm = LlamaModel()
            >>> docs = [
            ...     {"text": "Art. 1º...", "regulation_id": "lei-8666-art-1"},
            ...     {"text": "Art. 2º...", "regulation_id": "lei-8666-art-2"}
            ... ]
            >>> response = llm.generate_with_context(
            ...     "O que diz a lei sobre licitações?",
            ...     context_documents=docs
            ... )
        """
        # Build context string
        context_str = self._build_context_string(context_documents)

        # Build prompt
        prompt = self._build_rag_prompt(query, context_str)

        # Use default system prompt for RAG if none provided
        if system_prompt is None:
            system_prompt = self._get_default_rag_system_prompt()

        # Generate
        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            **kwargs
        )

    def _build_context_string(self, documents: List[Dict]) -> str:
        """
        Build formatted context string from documents.

        Args:
            documents: List of document dictionaries

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "")
            reg_id = doc.get("regulation_id", f"documento-{i}")
            version = doc.get("version", "")

            # Format document
            doc_header = f"[{reg_id}"
            if version:
                doc_header += f" - Versão {version}"
            doc_header += "]"

            context_parts.append(f"{doc_header}\n{text}")

        return "\n\n".join(context_parts)

    def _build_rag_prompt(self, query: str, context: str) -> str:
        """
        Build RAG prompt from query and context.

        Args:
            query: User query
            context: Context string

        Returns:
            Complete prompt
        """
        prompt = f"""Você é um assistente especializado em regulamentação de aviação civil brasileira.

Sua tarefa é responder perguntas com base APENAS nas normas regulatórias fornecidas abaixo.
Sempre cite a fonte (número da lei/regulamento e artigo) quando mencionar informações.

Se a informação necessária para responder não estiver nas normas fornecidas, diga claramente
que não encontrou a informação nos documentos disponíveis.

=== NORMAS REGULATÓRIAS ===
{context}

=== PERGUNTA DO USUÁRIO ===
{query}

=== RESPOSTA ===
Baseado nas normas fornecidas:
"""
        return prompt

    def _get_default_rag_system_prompt(self) -> str:
        """
        Get default system prompt for RAG tasks.

        Returns:
            System prompt string
        """
        return (
            "Você é um assistente especializado em regulamentação de aviação civil brasileira. "
            "Responda sempre em português, de forma clara e precisa, citando as fontes. "
            "Seja factual e baseie suas respostas apenas nas informações fornecidas."
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Multi-turn chat conversation.

        Args:
            messages: List of messages with 'role' and 'content'
            temperature: Override default temperature
            top_p: Override default top_p
            max_tokens: Override default max_tokens

        Returns:
            Assistant's response

        Example:
            >>> llm = LlamaModel()
            >>> messages = [
            ...     {"role": "user", "content": "O que é RAG?"},
            ...     {"role": "assistant", "content": "RAG significa..."},
            ...     {"role": "user", "content": "Me dê um exemplo"}
            ... ]
            >>> response = llm.chat(messages)
        """
        # Build options
        options = self.default_options.copy()
        if temperature is not None:
            options["temperature"] = temperature
        if top_p is not None:
            options["top_p"] = top_p
        if max_tokens is not None:
            options["num_predict"] = max_tokens

        logger.debug(f"Multi-turn chat ({len(messages)} messages)")

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options=options
            )

            return response["message"]["content"]

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    def __repr__(self) -> str:
        """String representation of the model."""
        return (
            f"LlamaModel(model={self.model_name}, host={self.host}, "
            f"temp={self.temperature})"
        )


# ========================================
# Utility Functions
# ========================================

def generate_rag_response(
    query: str,
    context_documents: List[Dict],
    llm: LlamaModel = None,
    **kwargs
) -> str:
    """
    Helper function to generate RAG response.

    Args:
        query: User query
        context_documents: Retrieved context documents
        llm: LlamaModel instance (creates new if None)
        **kwargs: Additional arguments for generation

    Returns:
        Generated response
    """
    if llm is None:
        llm = LlamaModel()

    return llm.generate_with_context(
        query=query,
        context_documents=context_documents,
        **kwargs
    )


# ========================================
# Example Usage
# ========================================

if __name__ == "__main__":
    """Example usage of LlamaModel."""

    print("Initializing Llama model...")
    llm = LlamaModel()

    # Example 1: Simple generation
    print("\n=== Example 1: Simple Generation ===")
    prompt = "Explique em uma frase o que é Retrieval-Augmented Generation (RAG)."
    response = llm.generate(prompt)
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")

    # Example 2: Generation with system prompt
    print("\n=== Example 2: With System Prompt ===")
    system_prompt = "Você é um professor de ciência da computação. Explique conceitos de forma didática."
    prompt = "O que é um vector database?"
    response = llm.generate(
        prompt,
        system_prompt=system_prompt,
        temperature=0.7
    )
    print(f"System: {system_prompt}")
    print(f"Prompt: {prompt}")
    print(f"Response: {response}")

    # Example 3: RAG with context documents
    print("\n=== Example 3: RAG with Context ===")
    context_docs = [
        {
            "text": "Art. 1º Esta lei estabelece normas gerais sobre licitações e contratos administrativos.",
            "regulation_id": "lei-8666-art-1",
            "version": "1993-06-21"
        },
        {
            "text": "Art. 2º As obras e serviços serão precedidos de licitação.",
            "regulation_id": "lei-8666-art-2",
            "version": "1993-06-21"
        }
    ]

    query = "O que a lei diz sobre licitações?"
    response = llm.generate_with_context(
        query=query,
        context_documents=context_docs,
        temperature=0.3
    )
    print(f"Query: {query}")
    print(f"Context: {len(context_docs)} documents")
    print(f"Response: {response}")

    # Example 4: Multi-turn chat
    print("\n=== Example 4: Multi-turn Chat ===")
    messages = [
        {"role": "user", "content": "Qual a capital do Brasil?"},
        {"role": "assistant", "content": "A capital do Brasil é Brasília."},
        {"role": "user", "content": "Em que ano foi fundada?"}
    ]
    response = llm.chat(messages)
    print(f"Messages: {len(messages)} turns")
    print(f"Response: {response}")

    print("\n✓ All examples completed!")
