from pathlib import Path
from pprint import pformat

import typer as typer
import yaml
from loguru import logger

from automation.models import Config


def load_config(config: Path) -> Config:
    with open(config) as config_file:
        config = Config.parse_obj(yaml.load(config_file, Loader=yaml.CLoader))
        logger.debug(pformat(config.languages))
        return config


if __name__ == "__main__":
    typer.run(load_config)
