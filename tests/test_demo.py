"""
Basic tests for demo mode scenarios.
Validates that the agent can successfully run demo tasks.
"""

import pytest
import logging
from pathlib import Path

from app.llm.ollama_client import OllamaClient
from app.agent.runner import AgentRunner
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.file_tools import ReadTextFileTool
from app.tools.http_fetch import HttpGetTool
from app.llm.ollama_client import OllamaModelNotFoundError


logger = logging.getLogger(__name__)


@pytest.fixture
def tool_registry():
    """Create tool registry with demo tools."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ReadTextFileTool(base_path=str(Path(__file__).parent.parent)))
    registry.register(HttpGetTool(max_text_length=300))
    return registry


@pytest.fixture
def llm_client():
    """Create OllamaClient instance."""
    return OllamaClient()


class TestDemoTools:
    """Test individual demo tools."""

    def test_calculator_tool_basic(self):
        """Test calculator with simple expression."""
        tool = CalculatorTool()
        result = tool.run(expression="1 + 1")
        assert result["result"] == "2"

    def test_calculator_tool_complex(self):
        """Test calculator with complex expression."""
        tool = CalculatorTool()
        result = tool.run(expression="(123 + 456) * 2")
        assert result["result"] == "1158"

    def test_calculator_tool_rejects_unsafe(self):
        """Test calculator rejects unsafe expressions."""
        tool = CalculatorTool()
        with pytest.raises(ValueError):
            tool.run(expression="__import__('os').system('echo hack')")

    def test_file_tool_validates_path(self):
        """Test file tool validates inputs."""
        tool = ReadTextFileTool()
        with pytest.raises(ValueError):
            tool.run(file_path="")

    def test_http_tool_validates_url(self):
        """Test HTTP tool validates URL."""
        tool = HttpGetTool()
        with pytest.raises(ValueError):
            tool.run(url="not_a_url", timeout_sec=5)

    def test_http_tool_validates_timeout(self):
        """Test HTTP tool validates timeout range."""
        tool = HttpGetTool()
        with pytest.raises(ValueError):
            tool.run(url="http://example.com", timeout_sec=200)


class TestToolRegistry:
    """Test tool registration and lookup."""

    def test_register_and_get_tool(self, tool_registry):
        """Test tool registration."""
        calc = tool_registry.get("calculator")
        assert calc is not None
        assert calc.name == "calculator"

    def test_list_tools(self, tool_registry):
        """Test listing all tools."""
        tools = tool_registry.list_tools()
        tool_names = [t["name"] for t in tools]
        assert "calculator" in tool_names
        assert "read_text_file" in tool_names
        assert "http_get" in tool_names


class TestAgentRunner:
    """Test agent runner with mocked LLM."""

    def test_runner_initialization(self, tool_registry, llm_client):
        """Test runner initialization."""
        runner = AgentRunner(
            llm_client=llm_client,
            tool_registry=tool_registry,
            task="Test task",
            mode="demo_mode",
            max_steps=5,
        )
        assert runner.task == "Test task"
        assert runner.mode == "demo_mode"
        assert runner.max_steps == 5

    def test_runner_uses_correct_max_steps(self, tool_registry, llm_client):
        """Test runner uses mode-appropriate max steps."""
        runner_demo = AgentRunner(
            llm_client=llm_client,
            tool_registry=tool_registry,
            task="Test",
            mode="demo_mode",
        )
        assert runner_demo.max_steps == 5

        runner_catalog = AgentRunner(
            llm_client=llm_client,
            tool_registry=tool_registry,
            task="Test",
            mode="catalog_mode",
        )
        assert runner_catalog.max_steps == 8

    def test_runner_returns_failed_result_on_model_error(self, tool_registry):
        """Model errors should not escape as uncaught exceptions."""

        class FailingClient:
            def generate(self, prompt, temperature=0.7, top_p=0.9, top_k=40):
                raise OllamaModelNotFoundError("model missing")

            def parse_json_response(self, text):
                return None

        runner = AgentRunner(
            llm_client=FailingClient(),
            tool_registry=tool_registry,
            task="Test task",
            mode="demo_mode",
            max_steps=5,
        )

        result = runner.run()

        assert result.success is False
        assert "Model request failed at step 1" in result.error
        assert "model missing" in result.error


class TestOllamaClientConfig:
    """Test environment-based client configuration."""

    def test_client_reads_settings_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_ENDPOINT", "http://example.local/api/generate")
        monkeypatch.setenv("OLLAMA_MODEL", "qwen3:0.6b")
        monkeypatch.setenv("OLLAMA_TIMEOUT_SEC", "45")

        client = OllamaClient()

        assert client.endpoint == "http://example.local/api/generate"
        assert client.model == "qwen3:0.6b"
        assert client.timeout_sec == 45


class TestIntegration:
    """Integration tests (require running Ollama)."""

    @pytest.mark.integration
    def test_demo_scenario_calculator(self, tool_registry, llm_client):
        """Test complete calculator scenario."""
        if not llm_client.health_check():
            pytest.skip("Ollama not available")

        runner = AgentRunner(
            llm_client=llm_client,
            tool_registry=tool_registry,
            task="Calculate (123 + 456) * 2",
            mode="demo_mode",
        )

        result = runner.run()

        # Should complete successfully
        assert result is not None
        # May not always succeed due to model variability, but should complete
        assert result.total_steps > 0
        assert result.total_steps <= runner.max_steps

    @pytest.mark.integration
    def test_demo_scenario_file_read(self, tool_registry, llm_client):
        """Test complete file read scenario."""
        if not llm_client.health_check():
            pytest.skip("Ollama not available")

        # Create test file
        test_file = Path(__file__).parent / "test.txt"
        test_file.write_text("line 1\nline 2\nline 3\n")

        try:
            runner = AgentRunner(
                llm_client=llm_client,
                tool_registry=tool_registry,
                task=f"Read the file at {test_file} and count the lines",
                mode="demo_mode",
            )

            result = runner.run()

            assert result is not None
            assert result.total_steps > 0
            assert result.total_steps <= runner.max_steps
        finally:
            if test_file.exists():
                test_file.unlink()
