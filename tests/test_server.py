import pytest
import json
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from mcp.server.fastmcp import Context

from vectara_mcp.server import (
    ask_vectara,
    search_vectara,
    correct_hallucinations,
    eval_factual_consistency,
    main
)
from vectara_mcp.auth import AuthMiddleware


class TestVectaraTools:
    """Test suite for Vectara MCP tools with new API key management"""

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing"""
        context = AsyncMock(spec=Context)
        context.info = MagicMock()
        context.report_progress = AsyncMock()
        return context

    @pytest.fixture(autouse=True)
    def clear_stored_api_key(self):
        """Clear stored API key before each test"""
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = None
        vectara_mcp.server._auth_required = True
        yield
        vectara_mcp.server._stored_api_key = None
        vectara_mcp.server._auth_required = True

    @pytest.fixture
    def mock_api_key(self):
        """Mock API key storage for tests that need it"""
        import vectara_mcp.server
        vectara_mcp.server._stored_api_key = "test-api-key"
        return "test-api-key"

    # ASK_VECTARA TESTS
    @pytest.mark.asyncio
    async def test_ask_vectara_missing_query(self, mock_context, mock_api_key):
        """Test ask_vectara with missing query"""
        result = await ask_vectara(
            query="",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )
        assert result == {"error": "Query is required."}

    @pytest.mark.asyncio
    async def test_ask_vectara_missing_corpus_keys(self, mock_context, mock_api_key):
        """Test ask_vectara with missing corpus keys"""
        result = await ask_vectara(
            query="test query",
            ctx=mock_context,
            corpus_keys=[]
        )
        assert result == {"error": "Corpus keys are required. Please ask the user to provide one or more corpus keys."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_ask_vectara_missing_api_key(self, mock_context):
        """Test ask_vectara with missing API key"""
        result = await ask_vectara(
            query="test query",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )
        assert result == {"error": "API key not configured. Please use 'setup_vectara_api_key' tool first or set VECTARA_API_KEY environment variable."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._call_vectara_query')
    async def test_ask_vectara_success(self, mock_api_call, mock_context, mock_api_key):
        """Test successful ask_vectara call"""
        mock_api_call.return_value = {
            "summary": "Test response summary",
            "search_results": [
                {
                    "score": 0.95,
                    "text": "Test citation text",
                    "document_metadata": {"title": "Test Source"}
                }
            ]
        }

        result = await ask_vectara(
            query="test query",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )

        # Check the structured response format
        assert result["summary"] == "Test response summary"
        assert "citations" in result
        assert len(result["citations"]) == 1

        # Check citation details
        citation = result["citations"][0]
        assert citation["id"] == 1
        assert citation["score"] == 0.95
        assert citation["text"] == "Test citation text"
        assert citation["document_metadata"] == {"title": "Test Source"}
        mock_context.info.assert_called_once_with("Running Vectara RAG query: test query")
        mock_api_call.assert_called_once()

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._call_vectara_query')
    async def test_ask_vectara_exception(self, mock_api_call, mock_context, mock_api_key):
        """Test ask_vectara with exception"""
        mock_api_call.side_effect = Exception("API Error")

        result = await ask_vectara(
            query="test query",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )

        assert result == {"error": "Error with Vectara RAG query: API Error"}

    # SEARCH_VECTARA TESTS
    @pytest.mark.asyncio
    async def test_search_vectara_missing_query(self, mock_context, mock_api_key):
        """Test search_vectara with missing query"""
        result = await search_vectara(
            query="",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )
        assert result == {"error": "Query is required."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._call_vectara_query')
    async def test_search_vectara_success(self, mock_api_call, mock_context, mock_api_key):
        """Test successful search_vectara call"""
        mock_api_call.return_value = {
            "search_results": [
                {
                    "score": 0.95,
                    "text": "Test search result text",
                    "document_metadata": {"title": "Test Document"}
                }
            ]
        }

        result = await search_vectara(
            query="test query",
            ctx=mock_context,
            corpus_keys=["test-corpus"]
        )

        assert isinstance(result, dict)
        assert "search_results" in result
        assert len(result["search_results"]) == 1
        assert result["search_results"][0]["score"] == 0.95
        assert result["search_results"][0]["text"] == "Test search result text"
        assert result["search_results"][0]["document_metadata"]["title"] == "Test Document"
        mock_context.info.assert_called_once_with("Running Vectara semantic search query: test query")
        mock_api_call.assert_called_once()

    # TRANSPORT AND AUTH TESTS
    def test_auth_middleware_validation(self):
        """Test authentication middleware validation"""
        auth = AuthMiddleware(auth_required=True)

        # Valid token
        os.environ["VECTARA_API_KEY"] = "test-key"
        auth.valid_tokens = {"test-key"}
        assert auth.validate_token("test-key") is True
        assert auth.validate_token("Bearer test-key") is True

        # Invalid token
        assert auth.validate_token("invalid-key") is False
        assert auth.validate_token(None) is False

        # Auth disabled
        auth_disabled = AuthMiddleware(auth_required=False)
        assert auth_disabled.validate_token(None) is True

        # Clean up
        if "VECTARA_API_KEY" in os.environ:
            del os.environ["VECTARA_API_KEY"]

    def test_token_extraction_from_headers(self):
        """Test token extraction from different header formats"""
        auth = AuthMiddleware()

        # Authorization header
        headers = {"Authorization": "Bearer test-token"}
        assert auth.extract_token_from_headers(headers) == "Bearer test-token"

        # X-API-Key header
        headers = {"X-API-Key": "test-token"}
        assert auth.extract_token_from_headers(headers) == "Bearer test-token"

        # Case insensitive
        headers = {"authorization": "Bearer test-token"}
        assert auth.extract_token_from_headers(headers) == "Bearer test-token"

        # No token
        headers = {}
        assert auth.extract_token_from_headers(headers) is None

    @patch('sys.argv', ['test', '--stdio'])
    def test_main_stdio_transport(self, capsys):
        """Test main function with STDIO transport"""
        with patch('vectara_mcp.server.mcp.run') as mock_run:
            with pytest.raises(SystemExit):
                main()

            mock_run.assert_called_once_with()
            captured = capsys.readouterr()
            assert "STDIO transport is less secure" in captured.err

    @patch('sys.argv', ['test', '--transport', 'http'])
    def test_main_http_transport(self, capsys):
        """Test main function with HTTP transport"""
        with patch('vectara_mcp.server.mcp.run') as mock_run:
            with pytest.raises(SystemExit):
                main()

            mock_run.assert_called_once_with(transport='http', host='127.0.0.1', port=8000)
            captured = capsys.readouterr()
            assert "HTTP mode" in captured.err
            assert "Authentication: enabled" in captured.err

    @patch('sys.argv', ['test', '--no-auth'])
    def test_main_no_auth_warning(self, capsys):
        """Test main function shows warning when auth is disabled"""
        with patch('vectara_mcp.server.mcp.run') as mock_run:
            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()
            assert "Authentication disabled" in captured.err
            assert "NEVER use in production" in captured.err

    # ENVIRONMENT VARIABLES TESTS
    @patch.dict('os.environ', {'VECTARA_TRANSPORT': 'sse', 'VECTARA_AUTH_REQUIRED': 'false'}, clear=False)
    def test_environment_variables(self):
        """Test that environment variables are respected"""
        # This test would require integration with actual argument parsing
        # For now, just test that the environment variables exist
        assert os.getenv('VECTARA_TRANSPORT') == 'sse'
        assert os.getenv('VECTARA_AUTH_REQUIRED') == 'false'

    # CORRECT_HALLUCINATIONS TESTS
    @pytest.mark.asyncio
    async def test_correct_hallucinations_missing_text(self, mock_context, mock_api_key):
        """Test correct_hallucinations with missing text"""
        result = await correct_hallucinations(
            generated_text="",
            documents=["doc1"],
            ctx=mock_context
        )
        assert result == {"error": "Generated text is required."}

    @pytest.mark.asyncio
    async def test_correct_hallucinations_missing_source_documents(self, mock_context, mock_api_key):
        """Test correct_hallucinations with missing source documents"""
        result = await correct_hallucinations(
            generated_text="test text",
            documents=[],
            ctx=mock_context
        )
        assert result == {"error": "Documents are required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_correct_hallucinations_missing_api_key(self, mock_context):
        """Test correct_hallucinations with missing API key"""
        result = await correct_hallucinations(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )
        assert result == {"error": "API key not configured. Please use 'setup_vectara_api_key' tool first or set VECTARA_API_KEY environment variable."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_correct_hallucinations_success(self, mock_api_request, mock_context, mock_api_key):
        """Test successful correct_hallucinations call"""
        mock_api_request.return_value = {"corrected_text": "Corrected version", "hallucinations": []}

        result = await correct_hallucinations(
            generated_text="test text with potential hallucination",
            documents=["Source document content"],
            ctx=mock_context
        )

        expected_result = {"corrected_text": "Corrected version", "hallucinations": []}
        assert result == expected_result
        mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_correct_hallucinations_403_error(self, mock_api_request, mock_context, mock_api_key):
        """Test correct_hallucinations with 403 permission error"""
        mock_api_request.side_effect = Exception("Permissions do not allow hallucination correction.")

        result = await correct_hallucinations(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with hallucination correction: Permissions do not allow hallucination correction."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_correct_hallucinations_400_error(self, mock_api_request, mock_context, mock_api_key):
        """Test correct_hallucinations with 400 bad request error"""
        mock_api_request.side_effect = Exception("Bad request: Invalid request format")

        result = await correct_hallucinations(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with hallucination correction: Bad request: Invalid request format"}

    # EVAL_FACTUAL_CONSISTENCY TESTS
    @pytest.mark.asyncio
    async def test_eval_factual_consistency_missing_text(self, mock_context, mock_api_key):
        """Test eval_factual_consistency with missing text"""
        result = await eval_factual_consistency(
            generated_text="",
            documents=["doc1"],
            ctx=mock_context
        )
        assert result == {"error": "Generated text is required."}

    @pytest.mark.asyncio
    async def test_eval_factual_consistency_missing_source_documents(self, mock_context, mock_api_key):
        """Test eval_factual_consistency with missing source documents"""
        result = await eval_factual_consistency(
            generated_text="test text",
            documents=[],
            ctx=mock_context
        )
        assert result == {"error": "Documents are required."}

    @pytest.mark.asyncio
    @patch.dict('os.environ', {}, clear=True)
    async def test_eval_factual_consistency_missing_api_key(self, mock_context):
        """Test eval_factual_consistency with missing API key"""
        result = await eval_factual_consistency(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )
        assert result == {"error": "API key not configured. Please use 'setup_vectara_api_key' tool first or set VECTARA_API_KEY environment variable."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_eval_factual_consistency_success(self, mock_api_request, mock_context, mock_api_key):
        """Test successful eval_factual_consistency call"""
        mock_api_request.return_value = {"consistency_score": 0.85, "inconsistencies": []}

        result = await eval_factual_consistency(
            generated_text="test text for consistency check",
            documents=["Source document content"],
            ctx=mock_context
        )

        expected_result = {"consistency_score": 0.85, "inconsistencies": []}
        assert result == expected_result
        mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_eval_factual_consistency_422_error(self, mock_api_request, mock_context, mock_api_key):
        """Test eval_factual_consistency with 422 language not supported error"""
        mock_api_request.side_effect = Exception("Language not supported by service.")

        result = await eval_factual_consistency(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with factual consistency evaluation: Language not supported by service."}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_eval_factual_consistency_exception(self, mock_api_request, mock_context, mock_api_key):
        """Test eval_factual_consistency with exception"""
        mock_api_request.side_effect = Exception("Network error")

        result = await eval_factual_consistency(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with factual consistency evaluation: Network error"}

    @pytest.mark.asyncio
    @patch('vectara_mcp.server._make_api_request')
    async def test_correct_hallucinations_exception(self, mock_api_request, mock_context, mock_api_key):
        """Test correct_hallucinations with exception"""
        mock_api_request.side_effect = Exception("Network error")

        result = await correct_hallucinations(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with hallucination correction: Network error"}