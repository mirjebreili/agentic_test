from __future__ import annotations
import os
from pathlib import Path
import yaml
from jinja2 import Template

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "app" / "prompts"
OVERRIDES_DIR = ROOT / "app" / "prompts_overrides"

class Prompt:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.id = f"{filepath.parent.name}/{filepath.stem}"

        content = filepath.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            front_matter, self.body = parts[1], parts[2]
            self.meta = yaml.safe_load(front_matter) or {}
        else:
            self.meta = {}
            self.body = content

        self.template = Template(self.body)

    def render(self, **kwargs) -> str:
        # Basic validation
        for var in self.meta.get("inputs", []):
            if var not in kwargs:
                raise ValueError(f"Missing required input '{var}' for prompt {self.id}")
        return self.template.render(**kwargs)

class PromptRegistry:
    def __init__(self, base_dir: Path = PROMPTS_DIR, override_dir: Path = OVERRIDES_DIR):
        self.base_dir = base_dir
        self.override_dir = override_dir
        self._prompts = {}
        self._load_prompts()

    def _load_prompts(self):
        # Load base prompts
        for filepath in self.base_dir.rglob("*.md"):
            if filepath.is_file():
                prompt = Prompt(filepath)
                self._prompts[prompt.id] = prompt

        # Apply overrides
        env = os.environ.get("APP_ENV", "dev")
        env_override_dir = self.override_dir / env
        if env_override_dir.exists():
            for filepath in env_override_dir.rglob("*.md"):
                if filepath.is_file():
                    override_prompt = Prompt(filepath)
                    if override_prompt.id in self._prompts:
                        print(f"Overriding prompt: {override_prompt.id}")
                        self._prompts[override_prompt.id] = override_prompt

    def get(self, prompt_id: str) -> Prompt:
        """Get a prompt by its ID (e.g., 'strategy/decide_method__v2')."""
        if prompt_id not in self._prompts:
            # Normalize path for different OS
            parts = prompt_id.split("/")
            filepath = self.base_dir.joinpath(*parts)
            if not str(filepath).endswith(".md"):
                filepath = Path(str(filepath) + ".md")

            if filepath.exists():
                prompt = Prompt(filepath)
                self._prompts[prompt_id] = prompt
            else:
                raise KeyError(f"Prompt '{prompt_id}' not found.")

        return self._prompts[prompt_id]

# Singleton instance
prompt_registry = PromptRegistry()
