import json
from pathlib import Path

from automation.models import Config


def load_json_config(config_path: Path) -> Config:
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    return Config.model_validate(
        {
            "source": {"project": "dwarf-fortress-steam"},
            "languages": config_data["include"],
        },
    )
