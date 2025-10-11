import codecs
import io
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import alternative_encodings
import typer
from df_translation_toolkit.convert import hardcoded_po_to_csv, objects_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from df_translation_toolkit.utils.po_utils import simple_read_po
from df_translation_toolkit.validation.validation_models import Diagnostics
from loguru import logger

from automation.load_config import load_config
from automation.models import Context, LanguageInfo

alternative_encodings.register_all()


def get_po_file_path(*, working_directory: Path, project_name: str, resource_name: str, language_code: str) -> Path:
    return (
        working_directory
        / "translations-backup"
        / "translations"
        / project_name
        / resource_name
        / f"{language_code}.po"
    )


def load_po_file(file_path: Path) -> list[tuple[str, str]]:
    with file_path.open(encoding="utf-8") as file:
        return simple_read_po(file)


def process_hardcoded(*, csv_file_path: Path, language: LanguageInfo, context: Context) -> Iterable[tuple[str, str]]:
    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name="hardcoded_steam",
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    prepared_dictionary = hardcoded_po_to_csv.prepare_dictionary(po_data)

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(cast("Iterable[list[str]]", prepared_dictionary))

    with csv_file_path.open("wb") as csv_file:
        csv_file.write(codecs.encode(csv_data_buffer.getvalue(), encoding=language.encoding))

    return prepared_dictionary


def process_objects(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    context: Context,
    exclude: set[str] | None = None,
) -> None:
    if not exclude:
        exclude = set()

    csv_directory = csv_file_path.parent
    errors_file_path = csv_directory / "errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name="objects",
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    po_data = [(source, translation) for source, translation in po_data if source not in exclude]

    diagnostics = Diagnostics()
    prepared_dictionary = objects_po_to_csv.prepare_dictionary(po_data, diagnostics)
    filtered_dictionary = {source: translation for source, translation in prepared_dictionary if source not in exclude}

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(cast("Iterable[list[str]]", filtered_dictionary.items()))

    if diagnostics.contains_problems():
        with errors_file_path.open("w", encoding="utf-8") as errors_file:
            errors_file.write(str(diagnostics))

    with csv_file_path.open("ab") as csv_file:
        csv_file.write(codecs.encode(csv_data_buffer.getvalue(), encoding=language.encoding))


@logger.catch(reraise=True)
def process(language: LanguageInfo, context: Context) -> None:
    translation_build_directory = context.working_directory / "translation_build"
    csv_directory = translation_build_directory / "csv" / language.name
    csv_directory.mkdir(parents=True, exist_ok=True)
    hardcoded_csv_file_path = csv_directory / "dfint_dictionary.csv"
    csv_hardcoded_data = process_hardcoded(
        csv_file_path=hardcoded_csv_file_path,
        language=language,
        context=context,
    )

    logger.info(f"{hardcoded_csv_file_path.relative_to(context.working_directory)} written")

    exclude = {first for first, _ in csv_hardcoded_data}

    csv_with_objects_directory = translation_build_directory / "csv_with_objects" / language.name
    csv_with_objects_directory.mkdir(parents=True, exist_ok=True)

    with_objects_csv_file_path = csv_with_objects_directory / "dfint_dictionary.csv"
    shutil.copy(hardcoded_csv_file_path, with_objects_csv_file_path)

    process_objects(
        csv_file_path=with_objects_csv_file_path,
        language=language,
        context=context,
        exclude=exclude,
    )

    logger.info(f"{with_objects_csv_file_path.relative_to(context.working_directory)} written")


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
