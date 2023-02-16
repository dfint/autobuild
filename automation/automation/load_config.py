from pathlib import Path
from pprint import pprint

import typer as typer
import yaml


def main(config: Path):
    with open(config) as config_file:
        config = yaml.load(config_file, Loader=yaml.CLoader)
        pprint(config)


if __name__ == "__main__":
    typer.run(main)
