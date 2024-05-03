from pathlib import Path

import strictyaml
import typer

from automation.models import Config


def load_config(config_path: Path) -> Config:
    with open(config_path) as config_file:
        yaml = strictyaml.load(config_file.read())
        config = Config.model_validate(yaml.data)
        return config


def main(config_path: Path) -> None:
    from pprint import pprint

    pprint(load_config(config_path).model_dump(), width=120)


if __name__ == "__main__":
    typer.run(main)
