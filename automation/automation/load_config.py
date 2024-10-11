from pathlib import Path

import strictyaml
import typer

from automation.models import Config


def load_config(config_path: Path) -> Config:
    yaml = strictyaml.load(config_path.read_text())
    return Config.model_validate(yaml.data)


def main(config_path: Path) -> None:
    from pprint import pprint

    pprint(load_config(config_path).model_dump(), width=120)


if __name__ == "__main__":
    typer.run(main)
