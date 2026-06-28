from pathlib import Path

import typer

from automation.load_config import load_config
from automation.models import Context
from automation.process import process


def process_all(context: Context) -> None:
    for language in context.config.languages:
        process(language, context)


app = typer.Typer()


@app.command()
def main(working_directory: Path) -> None:
    config = load_config(working_directory / "config.yaml")
    context = Context(config=config, working_directory=working_directory)
    process_all(context)


if __name__ == "__main__":
    app()
