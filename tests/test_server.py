import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import os
import aiohttp
from mcp.server.fastmcp import Context

from vectara_mcp.server import (
    ask_vectara,
    search_vectara,
    correct_hallucinations,
    eval_factual_consistency
)


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
        yield
        vectara_mcp.server._stored_api_key = None

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
    @patch('aiohttp.ClientSession.post')
    async def test_eval_factual_consistency_success(self, mock_post, mock_context, mock_api_key):
        """Test successful eval_factual_consistency call"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"consistency_score": 0.85, "inconsistencies": []}
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await eval_factual_consistency(
            generated_text="test text for consistency check",
            documents=["Source document content"],
            ctx=mock_context
        )

        expected_result = {"consistency_score": 0.85, "inconsistencies": []}
        assert result == expected_result
        mock_context.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_eval_factual_consistency_422_error(self, mock_post, mock_context, mock_api_key):
        """Test eval_factual_consistency with 422 language not supported error"""
        mock_response = AsyncMock()
        mock_response.status = 422
        mock_post.return_value.__aenter__.return_value = mock_response

        result = await eval_factual_consistency(
            generated_text="test text",
            documents=["doc1"],
            ctx=mock_context
        )

        assert result == {"error": "Error with factual consistency evaluation: Language not supported by service."}

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_eval_factual_consistency_exception(self, mock_post, mock_context, mock_api_key):
        """Test eval_factual_consistency with exception"""
        mock_post.side_effect = Exception("Network error")

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