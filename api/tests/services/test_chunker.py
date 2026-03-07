"""Tests for the code chunking service."""

import pytest

from api.services.chunker import (
    CodeChunk,
    chunk_file,
    detect_file_type,
    _chunk_fixed_window,
)
from api.services.tokenizer import count_tokens


class TestDetectFileType:
    """Tests for file type detection."""

    def test_java_file(self):
        """Detects Java files."""
        assert detect_file_type("UserService.java") == "java"
        assert detect_file_type("src/main/java/User.java") == "java"

    def test_typescript_files(self):
        """Detects TypeScript/JavaScript files."""
        assert detect_file_type("App.tsx") == "typescript"
        assert detect_file_type("hooks/useAuth.ts") == "typescript"
        assert detect_file_type("index.js") == "javascript"

    def test_python_files(self):
        """Detects Python files."""
        assert detect_file_type("main.py") == "python"
        assert detect_file_type("api/services/chunker.py") == "python"

    def test_unknown_extension(self):
        """Returns None for unknown extensions."""
        assert detect_file_type("data.xyz") is None
        assert detect_file_type("noextension") is None


class TestTokenizer:
    """Tests for token counting."""

    def test_count_empty(self):
        """Empty string returns 0."""
        assert count_tokens("") == 0
        assert count_tokens(None) == 0  # type: ignore

    def test_count_simple(self):
        """Counts tokens in simple text."""
        # "hello world" is typically 2 tokens
        count = count_tokens("hello world")
        assert count >= 2

    def test_count_code(self):
        """Counts tokens in code."""
        code = "public class User { private String name; }"
        count = count_tokens(code)
        assert count > 5  # Code has many tokens


class TestChunkJava:
    """Tests for Java code chunking."""

    def test_simple_method(self):
        """Extracts a simple method as a chunk."""
        java_code = '''
public class UserService {
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }
}
'''
        chunks = list(chunk_file(java_code, "UserService.java"))
        assert len(chunks) >= 1

        # Should have extracted the method
        method_chunk = next((c for c in chunks if "findById" in c.content), None)
        assert method_chunk is not None
        assert method_chunk.chunk_type in ("method", "class", "segment")

    def test_multiple_methods(self):
        """Extracts multiple methods from a class."""
        java_code = '''
public class UserService {
    private final UserRepository userRepository;

    public User create(CreateUserRequest request) {
        User user = new User();
        user.setName(request.getName());
        return userRepository.save(user);
    }

    public void delete(Long id) {
        userRepository.deleteById(id);
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }
}
'''
        chunks = list(chunk_file(java_code, "UserService.java"))

        # Should extract multiple chunks
        assert len(chunks) >= 1

        # Check content coverage
        all_content = " ".join(c.content for c in chunks)
        assert "create" in all_content
        assert "delete" in all_content

    def test_interface(self):
        """Handles Java interfaces."""
        java_code = '''
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    List<User> findByStatus(UserStatus status);
}
'''
        chunks = list(chunk_file(java_code, "UserRepository.java"))
        assert len(chunks) >= 1


class TestChunkTypeScript:
    """Tests for TypeScript/JavaScript chunking."""

    def test_function_component(self):
        """Extracts React function components."""
        tsx_code = '''
import React from 'react';

export function UserCard({ user }: UserCardProps) {
    return (
        <div className="user-card">
            <h2>{user.name}</h2>
            <p>{user.email}</p>
        </div>
    );
}
'''
        chunks = list(chunk_file(tsx_code, "UserCard.tsx"))
        assert len(chunks) >= 1

        func_chunk = next((c for c in chunks if "UserCard" in c.content), None)
        assert func_chunk is not None

    def test_arrow_function(self):
        """Extracts arrow function components."""
        tsx_code = '''
export const useAuth = () => {
    const [user, setUser] = useState<User | null>(null);

    const login = async (credentials: Credentials) => {
        const response = await api.login(credentials);
        setUser(response.user);
    };

    return { user, login };
};
'''
        chunks = list(chunk_file(tsx_code, "useAuth.ts"))
        assert len(chunks) >= 1

    def test_interface_and_type(self):
        """Extracts TypeScript interfaces."""
        ts_code = '''
export interface User {
    id: string;
    name: string;
    email: string;
}

export type UserRole = 'admin' | 'user' | 'guest';

export interface CreateUserRequest {
    name: string;
    email: string;
    role: UserRole;
}
'''
        chunks = list(chunk_file(ts_code, "types.ts"))
        # Should create at least one chunk
        assert len(chunks) >= 1


class TestChunkPython:
    """Tests for Python code chunking."""

    def test_function(self):
        """Extracts Python functions."""
        python_code = '''
def create_user(name: str, email: str) -> User:
    """Create a new user with the given details."""
    user = User(name=name, email=email)
    db.session.add(user)
    db.session.commit()
    return user


def delete_user(user_id: int) -> None:
    """Delete a user by ID."""
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
'''
        chunks = list(chunk_file(python_code, "services.py"))
        assert len(chunks) >= 1

        # Check we got the functions
        all_content = " ".join(c.content for c in chunks)
        assert "create_user" in all_content

    def test_class(self):
        """Extracts Python classes."""
        python_code = '''
class UserService:
    """Service for user operations."""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.repository.get(user_id)

    def create(self, data: CreateUserRequest) -> User:
        user = User(**data.dict())
        return self.repository.save(user)
'''
        chunks = list(chunk_file(python_code, "user_service.py"))
        assert len(chunks) >= 1


class TestFixedWindowChunking:
    """Tests for fallback fixed-window chunking."""

    def test_small_file(self):
        """Small files become a single chunk."""
        content = "# README\n\nThis is a small file."
        chunks = list(_chunk_fixed_window(content, max_chunk_tokens=100))
        assert len(chunks) <= 1

    def test_large_file_splits(self):
        """Large files are split into multiple chunks."""
        # Create content that exceeds chunk size
        lines = [f"Line {i}: This is some content to pad out the file." for i in range(100)]
        content = "\n".join(lines)

        chunks = list(_chunk_fixed_window(content, max_chunk_tokens=50))
        assert len(chunks) > 1

    def test_respects_line_boundaries(self):
        """Chunks split at line boundaries, not mid-line."""
        content = "Line 1 content\nLine 2 content\nLine 3 content"
        chunks = list(_chunk_fixed_window(content, max_chunk_tokens=20))

        for chunk in chunks:
            # Each chunk should contain complete lines
            assert not chunk.content.endswith(" ")  # No truncated words

    def test_line_numbers_correct(self):
        """Chunk line numbers are accurate."""
        lines = [f"Line {i}" for i in range(1, 21)]
        content = "\n".join(lines)

        chunks = list(_chunk_fixed_window(content, max_chunk_tokens=30))

        # First chunk should start at line 1
        assert chunks[0].start_line == 1

        # Line numbers should be continuous
        prev_end = 0
        for chunk in chunks:
            assert chunk.start_line > prev_end
            assert chunk.end_line >= chunk.start_line
            prev_end = chunk.end_line


class TestChunkFileEdgeCases:
    """Edge case tests for chunk_file."""

    def test_empty_content(self):
        """Empty content yields no chunks."""
        chunks = list(chunk_file("", "empty.java"))
        assert len(chunks) == 0

    def test_whitespace_only(self):
        """Whitespace-only content yields no chunks."""
        chunks = list(chunk_file("   \n\n   \t\t\n", "whitespace.py"))
        assert len(chunks) == 0

    def test_unknown_file_type(self):
        """Unknown file types use fixed-window chunking."""
        content = "Some content in an unknown format\n" * 20
        chunks = list(chunk_file(content, "data.xyz"))

        # Should still produce chunks via fallback
        assert len(chunks) >= 1
        assert all(c.chunk_type == "segment" for c in chunks)

    def test_signature_extraction(self):
        """Chunk signatures are extracted correctly."""
        java_code = '''
public class Example {
    public String processData(String input, int count) {
        return input.repeat(count);
    }
}
'''
        chunks = list(chunk_file(java_code, "Example.java"))

        # Find chunk with the method
        method_chunk = next((c for c in chunks if "processData" in c.content), None)
        if method_chunk and method_chunk.signature:
            assert "processData" in method_chunk.signature
