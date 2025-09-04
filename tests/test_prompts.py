import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.prompts import Prompt, PromptRegistry

@pytest.fixture
def mock_prompts(tmp_path: Path):
    """Fixture to create a temporary prompt directory structure."""
    base_dir = tmp_path / "prompts"
    override_dir = tmp_path / "prompts_overrides"

    # Create strategy prompt
    (base_dir / "strategy").mkdir(parents=True)
    prompt_meta = (
        "id: strategy/decide__v1\n"
        "version: 1.0\n"
        "role: user\n"
        "description: A test prompt\n"
        "inputs: [instrument]\n"
        "output_format: text\n"
        "tools_required: false\n"
    )
    (base_dir / "strategy" / "decide__v1.md").write_text(
        f"---\n{prompt_meta}---\nAnalyze {{ instrument }}."
    )

    # Create override for dev environment
    (override_dir / "dev" / "strategy").mkdir(parents=True)
    (override_dir / "dev" / "strategy" / "decide__v1.md").write_text(
        f"---\n{prompt_meta}---\nOVERRIDDEN: Analyze {{ instrument }}."
    )

    return base_dir, override_dir

def test_prompt_loading_and_rendering():
    """Test that a prompt is loaded and rendered correctly."""
    prompt_content = (
        "---\n"
        "id: test_prompt\n"
        "version: 1.0\n"
        "role: user\n"
        "description: A test prompt\n"
        "inputs: [name]\n"
        "output_format: text\n"
        "tools_required: false\n"
        "---\n"
        "Hello, {{ name }}!"
    )
    prompt = Prompt(MagicMock(read_text=lambda: prompt_content, parent=MagicMock(name="test"), stem="test_prompt"))
    rendered = prompt.render(name="World")
    assert "Hello, World!" in rendered

def test_prompt_registry(mock_prompts):
    """Test the prompt registry, including overrides."""
    base_dir, override_dir = mock_prompts

    # Test with override
    with patch.dict(os.environ, {"APP_ENV": "dev"}):
        registry = PromptRegistry(base_dir, override_dir)
        prompt = registry.get("strategy/decide__v1")
        assert "OVERRIDDEN" in prompt.body

    # Test without override
    with patch.dict(os.environ, {"APP_ENV": "prod"}):
        registry = PromptRegistry(base_dir, override_dir)
        prompt = registry.get("strategy/decide__v1")
        assert "OVERRIDDEN" not in prompt.body
