
from pathlib import Path

import typer
from df_translation_toolkit.convert import text_to_mo
from df_translation_toolkit.validation.validation_models import Diagnostics
from loguru import logger

from automation.load_config import load_config
from automation.models import Context, LanguageInfo
from automation.utils import get_po_file_path


def process_resource(mo_directory: Path, language: LanguageInfo, resource: str, context: Context) -> None:
    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name=resource,
        language_code=language.code,
    )
    mo_file_path = mo_directory / f"{resource}.mo"
    diagnostics = Diagnostics()
    with po_file_path.open("rt", encoding="utf-8") as po_file, mo_file_path.open("wb") as mo_file:
        text_to_mo.convert(po_file, mo_file, diagnostics)

    errors_file_path = mo_directory / f"{resource}_errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

    if diagnostics.contains_problems():
        with errors_file_path.open("w", encoding="utf-8") as errors_file:
            errors_file.write(str(diagnostics))


@logger.catch(reraise=True)
def process_language(language: LanguageInfo, context: Context) -> None:
    mo_directory = context.destintion_directory / "mo" / language.name
    mo_directory.mkdir(parents=True, exist_ok=True)
    for resource in ("objects", "text_set"):
        process_resource(mo_directory, language, resource, context)


def process_all(context: Context) -> None:
    for language in context.config.languages:
        process_language(language, context)


app = typer.Typer()


@app.command()
def main(working_directory: Path, destination_directory: Path) -> None:
    config = load_config(working_directory / "config.yaml")
    context = Context(config=config, working_directory=working_directory, destintion_directory=destination_directory)
    process_all(context)


if __name__ == "__main__":
    app()
