from pathlib import Path
from pprint import pprint

import typer as typer
import yaml

from automation.models import Config


def main(config: Path):
    with open(config) as config_file:
        config = Config.parse_obj(yaml.load(config_file, Loader=yaml.CLoader))
        pprint(config.languages)


if __name__ == "__main__":
    typer.run(main)
