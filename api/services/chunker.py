"""Code chunking service for splitting files into retrievable segments.

Parses source code to extract functions, classes, and methods as individual
chunks. Falls back to fixed-size windowing for unsupported file types.
"""

import logging
import re
from dataclasses import dataclass
from typing import Generator

from api.services.tokenizer import count_tokens

logger = logging.getLogger(__name__)

# Maximum tokens per chunk (leaves room for other context)
DEFAULT_MAX_CHUNK_TOKENS = 300

# Minimum tokens for a chunk to be worth storing
MIN_CHUNK_TOKENS = 10


@dataclass
class CodeChunk:
    """A parsed chunk of source code.

    Attributes:
        content: The source code content.
        chunk_type: Type of chunk (function, class, method, segment).
        signature: Function/class signature for search boosting.
        start_line: Starting line number (1-based).
        end_line: Ending line number (1-based).
        token_count: Number of tokens in content.
    """
    content: str
    chunk_type: str
    signature: str | None
    start_line: int
    end_line: int
    token_count: int


# Language-specific patterns for extracting code structures
JAVA_PATTERNS = {
    "class": re.compile(
        r'^(\s*)(public\s+|private\s+|protected\s+)?'
        r'(abstract\s+|final\s+)?'
        r'(class|interface|enum|record)\s+'
        r'(\w+)',
        re.MULTILINE
    ),
    "method": re.compile(
        r'^(\s*)(public\s+|private\s+|protected\s+)?'
        r'(static\s+)?(final\s+)?'
        r'([\w<>\[\],\s]+)\s+'  # return type
        r'(\w+)\s*'  # method name
        r'\([^)]*\)',  # parameters
        re.MULTILINE
    ),
}

TYPESCRIPT_PATTERNS = {
    "class": re.compile(
        r'^(\s*)(export\s+)?(default\s+)?'
        r'(abstract\s+)?'
        r'class\s+'
        r'(\w+)',
        re.MULTILINE
    ),
    "function": re.compile(
        r'^(\s*)(export\s+)?(default\s+)?'
        r'(async\s+)?'
        r'function\s+'
        r'(\w+)\s*'
        r'(<[^>]*>)?'  # generics
        r'\([^)]*\)',
        re.MULTILINE
    ),
    "arrow": re.compile(
        r'^(\s*)(export\s+)?'
        r'(const|let|var)\s+'
        r'(\w+)\s*'
        r'(:\s*[\w<>\[\]|&\s]+)?\s*'  # type annotation
        r'=\s*'
        r'(async\s+)?'
        r'(\([^)]*\)|[\w]+)\s*'  # params
        r'(:\s*[\w<>\[\]|&\s]+)?\s*'  # return type
        r'=>',
        re.MULTILINE
    ),
    "interface": re.compile(
        r'^(\s*)(export\s+)?'
        r'(interface|type)\s+'
        r'(\w+)',
        re.MULTILINE
    ),
}

PYTHON_PATTERNS = {
    "class": re.compile(
        r'^(\s*)class\s+(\w+)',
        re.MULTILINE
    ),
    "function": re.compile(
        r'^(\s*)(async\s+)?def\s+(\w+)\s*\(',
        re.MULTILINE
    ),
}


def detect_file_type(file_path: str) -> str | None:
    """Detect the programming language from file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Language identifier (java, typescript, python, etc.) or None.
    """
    ext_map = {
        ".java": "java",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".py": "python",
        ".kt": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".cs": "csharp",
        ".rb": "ruby",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
    }

    # Extract extension
    if "." not in file_path:
        return None
    ext = "." + file_path.rsplit(".", 1)[-1].lower()
    return ext_map.get(ext)


def chunk_file(
    content: str,
    file_path: str,
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
) -> Generator[CodeChunk, None, None]:
    """Split a source file into semantic chunks.

    Attempts language-aware parsing first, falls back to fixed-size
    windowing for unsupported languages or parsing failures.

    Args:
        content: The file content.
        file_path: Path to the file (for language detection).
        max_chunk_tokens: Maximum tokens per chunk.

    Yields:
        CodeChunk instances representing file segments.
    """
    if not content or not content.strip():
        return

    file_type = detect_file_type(file_path)
    logger.debug("Chunking %s (detected type: %s)", file_path, file_type)

    # Try language-specific chunking
    if file_type == "java":
        chunks = list(_chunk_java(content, max_chunk_tokens))
        if chunks:
            yield from chunks
            return
    elif file_type in ("typescript", "javascript"):
        chunks = list(_chunk_typescript(content, max_chunk_tokens))
        if chunks:
            yield from chunks
            return
    elif file_type == "python":
        chunks = list(_chunk_python(content, max_chunk_tokens))
        if chunks:
            yield from chunks
            return

    # Fallback: fixed-size windowing
    yield from _chunk_fixed_window(content, max_chunk_tokens)


def _chunk_java(content: str, max_chunk_tokens: int) -> Generator[CodeChunk, None, None]:
    """Chunk Java source code by class and method boundaries.

    Args:
        content: Java source code.
        max_chunk_tokens: Maximum tokens per chunk.

    Yields:
        CodeChunk instances for each method/class.
    """
    lines = content.split("\n")

    # Find method boundaries using brace matching
    chunks = _extract_braced_blocks(lines, JAVA_PATTERNS["method"], "method", max_chunk_tokens)

    if not chunks:
        # Fall back to class-level chunking
        chunks = _extract_braced_blocks(lines, JAVA_PATTERNS["class"], "class", max_chunk_tokens)

    yield from chunks


def _chunk_typescript(content: str, max_chunk_tokens: int) -> Generator[CodeChunk, None, None]:
    """Chunk TypeScript/JavaScript source code.

    Args:
        content: TypeScript/JavaScript source code.
        max_chunk_tokens: Maximum tokens per chunk.

    Yields:
        CodeChunk instances for each function/class/component.
    """
    lines = content.split("\n")

    # Try functions first
    chunks = list(_extract_braced_blocks(lines, TYPESCRIPT_PATTERNS["function"], "function", max_chunk_tokens))

    # Add arrow functions
    chunks.extend(_extract_braced_blocks(lines, TYPESCRIPT_PATTERNS["arrow"], "function", max_chunk_tokens))

    # Add classes
    chunks.extend(_extract_braced_blocks(lines, TYPESCRIPT_PATTERNS["class"], "class", max_chunk_tokens))

    # Sort by line number and deduplicate overlaps
    chunks.sort(key=lambda c: c.start_line)
    yield from _deduplicate_chunks(chunks)


def _chunk_python(content: str, max_chunk_tokens: int) -> Generator[CodeChunk, None, None]:
    """Chunk Python source code by function and class definitions.

    Args:
        content: Python source code.
        max_chunk_tokens: Maximum tokens per chunk.

    Yields:
        CodeChunk instances for each function/class.
    """
    lines = content.split("\n")

    # Python uses indentation, not braces
    chunks = _extract_indented_blocks(lines, PYTHON_PATTERNS["function"], "function", max_chunk_tokens)
    chunks.extend(_extract_indented_blocks(lines, PYTHON_PATTERNS["class"], "class", max_chunk_tokens))

    chunks.sort(key=lambda c: c.start_line)
    yield from _deduplicate_chunks(chunks)


def _extract_braced_blocks(
    lines: list[str],
    pattern: re.Pattern,
    chunk_type: str,
    max_chunk_tokens: int,
) -> list[CodeChunk]:
    """Extract code blocks delimited by braces.

    Args:
        lines: Source code lines.
        pattern: Regex pattern to match block starts.
        chunk_type: Type label for chunks.
        max_chunk_tokens: Maximum tokens per chunk.

    Returns:
        List of extracted CodeChunk instances.
    """
    chunks = []
    content = "\n".join(lines)

    for match in pattern.finditer(content):
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1

        # Find the opening brace
        brace_pos = content.find("{", match.end())
        if brace_pos == -1:
            continue

        # Match braces to find block end
        depth = 1
        pos = brace_pos + 1
        while pos < len(content) and depth > 0:
            if content[pos] == "{":
                depth += 1
            elif content[pos] == "}":
                depth -= 1
            pos += 1

        if depth != 0:
            continue

        end_line = content[:pos].count("\n") + 1
        block_content = content[start_pos:pos]

        # Extract signature (first line of match)
        signature = match.group(0).strip()

        # Check token count
        token_count = count_tokens(block_content)

        if token_count < MIN_CHUNK_TOKENS:
            continue

        if token_count > max_chunk_tokens:
            # Split large blocks into smaller chunks
            sub_chunks = list(_chunk_fixed_window(
                block_content,
                max_chunk_tokens,
                start_line_offset=start_line - 1,
                chunk_type=chunk_type,
                signature=signature,
            ))
            chunks.extend(sub_chunks)
        else:
            chunks.append(CodeChunk(
                content=block_content,
                chunk_type=chunk_type,
                signature=signature,
                start_line=start_line,
                end_line=end_line,
                token_count=token_count,
            ))

    return chunks


def _extract_indented_blocks(
    lines: list[str],
    pattern: re.Pattern,
    chunk_type: str,
    max_chunk_tokens: int,
) -> list[CodeChunk]:
    """Extract Python-style indentation-based blocks.

    Args:
        lines: Source code lines.
        pattern: Regex pattern to match block starts.
        chunk_type: Type label for chunks.
        max_chunk_tokens: Maximum tokens per chunk.

    Returns:
        List of extracted CodeChunk instances.
    """
    chunks = []
    content = "\n".join(lines)

    for match in pattern.finditer(content):
        start_pos = match.start()
        start_line = content[:start_pos].count("\n")

        # Get the indentation of the definition
        base_indent = len(match.group(1)) if match.group(1) else 0

        # Find the end of the block (next line with same or less indentation)
        end_line = start_line
        for i, line in enumerate(lines[start_line + 1:], start=start_line + 1):
            if line.strip() == "":
                continue
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= base_indent and line.strip():
                break
            end_line = i

        block_lines = lines[start_line:end_line + 1]
        block_content = "\n".join(block_lines)

        # Extract signature
        signature = lines[start_line].strip()

        token_count = count_tokens(block_content)

        if token_count < MIN_CHUNK_TOKENS:
            continue

        if token_count > max_chunk_tokens:
            sub_chunks = list(_chunk_fixed_window(
                block_content,
                max_chunk_tokens,
                start_line_offset=start_line,
                chunk_type=chunk_type,
                signature=signature,
            ))
            chunks.extend(sub_chunks)
        else:
            chunks.append(CodeChunk(
                content=block_content,
                chunk_type=chunk_type,
                signature=signature,
                start_line=start_line + 1,
                end_line=end_line + 1,
                token_count=token_count,
            ))

    return chunks


def _chunk_fixed_window(
    content: str,
    max_chunk_tokens: int,
    start_line_offset: int = 0,
    chunk_type: str = "segment",
    signature: str | None = None,
) -> Generator[CodeChunk, None, None]:
    """Split content into fixed-size token windows at line boundaries.

    Args:
        content: The content to chunk.
        max_chunk_tokens: Maximum tokens per chunk.
        start_line_offset: Line number offset for chunk positions.
        chunk_type: Type label for chunks.
        signature: Optional signature for all chunks.

    Yields:
        CodeChunk instances of roughly equal size.
    """
    lines = content.split("\n")
    current_chunk_lines = []
    current_tokens = 0
    chunk_start_line = start_line_offset + 1

    for i, line in enumerate(lines):
        line_tokens = count_tokens(line + "\n")

        if current_tokens + line_tokens > max_chunk_tokens and current_chunk_lines:
            # Emit current chunk
            chunk_content = "\n".join(current_chunk_lines)
            if count_tokens(chunk_content) >= MIN_CHUNK_TOKENS:
                yield CodeChunk(
                    content=chunk_content,
                    chunk_type=chunk_type,
                    signature=signature,
                    start_line=chunk_start_line,
                    end_line=start_line_offset + i,
                    token_count=current_tokens,
                )

            # Start new chunk
            current_chunk_lines = [line]
            current_tokens = line_tokens
            chunk_start_line = start_line_offset + i + 1
        else:
            current_chunk_lines.append(line)
            current_tokens += line_tokens

    # Emit final chunk
    if current_chunk_lines:
        chunk_content = "\n".join(current_chunk_lines)
        token_count = count_tokens(chunk_content)
        if token_count >= MIN_CHUNK_TOKENS:
            yield CodeChunk(
                content=chunk_content,
                chunk_type=chunk_type,
                signature=signature,
                start_line=chunk_start_line,
                end_line=start_line_offset + len(lines),
                token_count=token_count,
            )


def _deduplicate_chunks(chunks: list[CodeChunk]) -> Generator[CodeChunk, None, None]:
    """Remove overlapping chunks, keeping the most specific.

    Args:
        chunks: List of potentially overlapping chunks.

    Yields:
        Non-overlapping chunks.
    """
    if not chunks:
        return

    # Sort by start line, then by size (smaller first = more specific)
    sorted_chunks = sorted(chunks, key=lambda c: (c.start_line, c.end_line - c.start_line))

    covered_lines = set()
    for chunk in sorted_chunks:
        chunk_lines = set(range(chunk.start_line, chunk.end_line + 1))

        # Skip if more than 50% overlaps with already covered lines
        overlap = len(chunk_lines & covered_lines)
        if overlap > len(chunk_lines) * 0.5:
            continue

        covered_lines.update(chunk_lines)
        yield chunk
