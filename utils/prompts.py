from pathlib import Path
from string import Formatter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = PROJECT_ROOT / "prompts"


def load_prompt(prompt_name: str, prompts_dir: Path | None = None) -> str:
    base_dir = prompts_dir or PROMPTS_DIR
    prompt_path = base_dir / prompt_name

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()


def render_prompt(template: str, **kwargs: Any) -> str:
    missing_keys = _get_missing_template_keys(template, kwargs)

    if missing_keys:
        raise KeyError(
            "Missing prompt placeholder values: "
            + ", ".join(sorted(missing_keys))
        )

    return template.format(**kwargs)


def load_and_render_prompt(
    prompt_name: str,
    prompts_dir: Path | None = None,
    **kwargs: Any,
) -> str:
    template = load_prompt(prompt_name, prompts_dir=prompts_dir)
    return render_prompt(template, **kwargs)


def _get_missing_template_keys(template: str, values: dict[str, Any]) -> set[str]:
    formatter = Formatter()
    required_keys = {
        field_name
        for _, field_name, _, _ in formatter.parse(template)
        if field_name
    }

    return required_keys - set(values.keys())