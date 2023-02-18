from pathlib import Path

import typer as typer
import yaml

from automation.models import Config


def load_config(config_path: Path) -> Config:
    with open(config_path) as config_file:
        config = Config.parse_obj(yaml.load(config_file, Loader=yaml.CLoader))
        return config


if __name__ == "__main__":
    typer.run(load_config)
