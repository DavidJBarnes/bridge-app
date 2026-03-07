"""TF-IDF based code chunk retrieval service.

Builds and queries a TF-IDF index over code chunks to find the most
relevant context for a given prompt. Optimized for code with custom
tokenization that preserves programming identifiers.
"""

import logging
import re
from dataclasses import dataclass
from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from sqlalchemy.orm import Session

from api.models.file_chunk import FileChunk
from api.models.project_file import ProjectFile
from api.services.tokenizer import count_tokens

logger = logging.getLogger(__name__)

# Default number of chunks to retrieve
DEFAULT_TOP_K = 5

# Maximum total tokens for retrieved context
DEFAULT_MAX_CONTEXT_TOKENS = 500


@dataclass
class RetrievedChunk:
    """A chunk retrieved by similarity search.

    Attributes:
        chunk: The FileChunk database record.
        file_path: Path of the containing file.
        score: Similarity score (0-1).
        content: The chunk content.
        token_count: Number of tokens in content.
    """
    chunk: FileChunk
    file_path: str
    score: float
    content: str
    token_count: int


class CodeTokenizer:
    """Custom tokenizer for code that preserves identifiers.

    Standard text tokenizers break on underscores and camelCase,
    losing important semantic information. This tokenizer:
    - Splits camelCase: getUserById -> get, User, By, Id
    - Splits snake_case: get_user_by_id -> get, user, by, id
    - Preserves common programming keywords
    - Lowercases everything for matching
    """

    # Pattern to split camelCase
    _CAMEL_PATTERN = re.compile(r'(?<!^)(?=[A-Z])')

    # Pattern to extract words (alphanumeric sequences)
    _WORD_PATTERN = re.compile(r'[a-zA-Z][a-zA-Z0-9]*')

    def __call__(self, text: str) -> list[str]:
        """Tokenize code text.

        Args:
            text: Source code or query text.

        Returns:
            List of lowercase tokens.
        """
        tokens = []

        # Extract all word-like sequences
        words = self._WORD_PATTERN.findall(text)

        for word in words:
            # Split camelCase
            parts = self._CAMEL_PATTERN.split(word)
            for part in parts:
                # Split snake_case (already handled by word extraction)
                # and add to tokens
                if len(part) >= 2:  # Skip single-char tokens
                    tokens.append(part.lower())

        return tokens


class ProjectRetriever:
    """TF-IDF retriever for a single project's chunks.

    Builds an in-memory TF-IDF index over all chunks in a project.
    The index is rebuilt when chunks change.

    Attributes:
        project_id: The project being indexed.
        vectorizer: The TF-IDF vectorizer.
        chunk_ids: Ordered list of chunk IDs matching matrix rows.
        tfidf_matrix: The TF-IDF document-term matrix.
    """

    def __init__(self, project_id: int):
        """Initialize retriever for a project.

        Args:
            project_id: The project ID to index.
        """
        self.project_id = project_id
        self.vectorizer = TfidfVectorizer(
            tokenizer=CodeTokenizer(),
            lowercase=True,
            max_features=10000,  # Limit vocabulary size
            min_df=1,  # Include rare terms (important for code)
            max_df=0.95,  # Exclude terms in >95% of docs
            ngram_range=(1, 2),  # Include bigrams for phrases
            token_pattern=None,  # Use custom tokenizer
        )
        self.chunk_ids: list[int] = []
        self.chunk_data: dict[int, dict] = {}  # chunk_id -> {content, file_path, token_count}
        self.tfidf_matrix = None
        self._is_fitted = False

    def build_index(self, db: Session) -> int:
        """Build or rebuild the TF-IDF index from database chunks.

        Args:
            db: Database session.

        Returns:
            Number of chunks indexed.
        """
        # Query all chunks for this project with file info
        chunks = (
            db.query(FileChunk, ProjectFile.file_path)
            .join(ProjectFile)
            .filter(ProjectFile.project_id == self.project_id)
            .order_by(FileChunk.id)
            .all()
        )

        if not chunks:
            logger.warning("No chunks found for project %d", self.project_id)
            self._is_fitted = False
            return 0

        # Prepare documents for TF-IDF
        self.chunk_ids = []
        self.chunk_data = {}
        documents = []

        for chunk, file_path in chunks:
            # Combine signature (boosted) and content for better matching
            doc_text = ""
            if chunk.signature:
                # Repeat signature to boost its importance
                doc_text = f"{chunk.signature} {chunk.signature} "
            doc_text += chunk.content

            documents.append(doc_text)
            self.chunk_ids.append(chunk.id)
            self.chunk_data[chunk.id] = {
                "content": chunk.content,
                "file_path": file_path,
                "token_count": chunk.token_count,
                "signature": chunk.signature,
                "chunk_type": chunk.chunk_type,
            }

        # Build TF-IDF matrix
        try:
            self.tfidf_matrix = self.vectorizer.fit_transform(documents)
            self._is_fitted = True
            logger.info(
                "Built TF-IDF index for project %d: %d chunks, %d features",
                self.project_id,
                len(documents),
                len(self.vectorizer.vocabulary_),
            )
        except ValueError as e:
            logger.error("Failed to build TF-IDF index: %s", e)
            self._is_fitted = False
            return 0

        return len(documents)

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    ) -> list[RetrievedChunk]:
        """Retrieve the most relevant chunks for a query.

        Args:
            query: The search query (user prompt or keywords).
            top_k: Maximum number of chunks to return.
            max_tokens: Maximum total tokens across all returned chunks.

        Returns:
            List of RetrievedChunk, ordered by relevance (highest first).
        """
        if not self._is_fitted or self.tfidf_matrix is None:
            logger.warning("Retriever not fitted, returning empty results")
            return []

        if not query.strip():
            return []

        # Transform query to TF-IDF vector
        try:
            query_vector = self.vectorizer.transform([query])
        except Exception as e:
            logger.error("Failed to vectorize query: %s", e)
            return []

        # Compute cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Get extra for filtering

        # Build results, respecting token budget
        results = []
        total_tokens = 0

        for idx in top_indices:
            if len(results) >= top_k:
                break

            score = similarities[idx]
            if score < 0.01:  # Skip very low relevance
                continue

            chunk_id = self.chunk_ids[idx]
            chunk_info = self.chunk_data[chunk_id]

            # Check token budget
            chunk_tokens = chunk_info["token_count"]
            if total_tokens + chunk_tokens > max_tokens:
                continue

            total_tokens += chunk_tokens

            # Create a minimal FileChunk for the result
            chunk = FileChunk(
                id=chunk_id,
                content=chunk_info["content"],
                signature=chunk_info["signature"],
                chunk_type=chunk_info["chunk_type"],
                token_count=chunk_tokens,
            )

            results.append(RetrievedChunk(
                chunk=chunk,
                file_path=chunk_info["file_path"],
                score=float(score),
                content=chunk_info["content"],
                token_count=chunk_tokens,
            ))

        logger.debug(
            "Retrieved %d chunks (%d tokens) for query: %s...",
            len(results),
            total_tokens,
            query[:50],
        )

        return results


# Cache of project retrievers
_retriever_cache: dict[int, ProjectRetriever] = {}


def get_retriever(project_id: int, db: Session, rebuild: bool = False) -> ProjectRetriever:
    """Get or create a retriever for a project.

    Retriever indices are cached in memory. Use rebuild=True after
    adding/updating chunks.

    Args:
        project_id: The project ID.
        db: Database session.
        rebuild: Force rebuild of the index.

    Returns:
        Configured ProjectRetriever instance.
    """
    if project_id not in _retriever_cache or rebuild:
        retriever = ProjectRetriever(project_id)
        retriever.build_index(db)
        _retriever_cache[project_id] = retriever

    return _retriever_cache[project_id]


def clear_retriever_cache(project_id: int | None = None):
    """Clear cached retrievers.

    Args:
        project_id: Specific project to clear, or None for all.
    """
    if project_id is None:
        _retriever_cache.clear()
    elif project_id in _retriever_cache:
        del _retriever_cache[project_id]


def retrieve_context(
    db: Session,
    project_id: int,
    query: str,
    top_k: int = DEFAULT_TOP_K,
    max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
) -> list[RetrievedChunk]:
    """Convenience function to retrieve relevant chunks.

    Args:
        db: Database session.
        project_id: The project to search.
        query: Search query.
        top_k: Maximum chunks to return.
        max_tokens: Maximum total tokens.

    Returns:
        List of relevant chunks.
    """
    retriever = get_retriever(project_id, db)
    return retriever.retrieve(query, top_k=top_k, max_tokens=max_tokens)


def format_context_for_prompt(chunks: Sequence[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context string for prompts.

    Args:
        chunks: Retrieved chunks to format.

    Returns:
        Formatted context string with file paths and content.
    """
    if not chunks:
        return ""

    parts = ["### Relevant Code Context\n"]

    for chunk in chunks:
        parts.append(f"\n#### {chunk.file_path}")
        if chunk.chunk.signature:
            parts.append(f"```\n{chunk.chunk.signature}\n```")
        parts.append(f"```\n{chunk.content}\n```\n")

    return "\n".join(parts)
