import asyncio
import codecs
import io
import shutil
from collections.abc import Iterable
from pathlib import Path

import alternative_encodings
import typer
from df_translation_toolkit.convert import hardcoded_po_to_csv, objects_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from df_translation_toolkit.utils.po_utils import simple_read_po
from loguru import logger

from automation.load_config import load_config
from automation.models import Config, LanguageInfo

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


async def convert_hardcoded(po_data: list[tuple[str, str]]) -> Iterable[tuple[str, str]]:
    return hardcoded_po_to_csv.prepare_dictionary(po_data)


async def convert_objects(po_data: bytes, errors_file: io.BytesIO) -> str:
    po_data = io.StringIO(po_data.decode(encoding="utf-8"))
    result = io.StringIO(newline="")
    await asyncio.to_thread(objects_po_to_csv.convert, po_data, result, errors_file)
    return result.getvalue()


def process_hardcoded(*, csv_file_path: Path, language: LanguageInfo, config: Config) -> Iterable[tuple[str, str]]:
    po_file_path = get_po_file_path(
        working_directory=config.working_directory,
        project_name=config.source.project,
        resource_name="hardcoded_steam",
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    prepared_dictionary = hardcoded_po_to_csv.prepare_dictionary(po_data)

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(prepared_dictionary)

    with csv_file_path.open("wb") as csv_file:
        csv_file.write(codecs.encode(csv_data_buffer.getvalue(), encoding=language.encoding))

    return prepared_dictionary


def process_objects(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    config: Config,
    exclude: set[str] | None = None,
) -> None:
    if not exclude:
        exclude = set()

    csv_directory = csv_file_path.parent
    errors_file_path = csv_directory / "errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

    po_file_path = get_po_file_path(
        working_directory=config.working_directory,
        project_name=config.source.project,
        resource_name="objects",
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    po_data = [(source, translation) for source, translation in po_data if source not in exclude]

    error_buffer = io.StringIO()
    prepared_dictionary = objects_po_to_csv.prepare_dictionary(po_data, error_buffer)
    filtered_dictionary = {source: translation for source, translation in prepared_dictionary if source not in exclude}

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(filtered_dictionary.items())

    errors = error_buffer.getvalue()
    if errors:
        with errors_file_path.open("w", encoding="utf-8") as errors_file:
            errors_file.write(errors)

    with csv_file_path.open("ab") as csv_file:
        csv_file.write(codecs.encode(csv_data_buffer.getvalue(), encoding=language.encoding))


@logger.catch(reraise=True)
async def process(language: LanguageInfo, config: Config) -> None:
    translation_build_directory = config.working_directory / "translation_build"
    csv_directory = translation_build_directory / "csv" / language.name
    csv_directory.mkdir(parents=True, exist_ok=True)
    hardcoded_csv_file_path = csv_directory / "dfint_dictionary.csv"
    csv_hardcoded_data = await asyncio.to_thread(
        process_hardcoded,
        csv_file_path=hardcoded_csv_file_path,
        language=language,
        config=config,
    )

    logger.info(f"{hardcoded_csv_file_path.relative_to(config.working_directory)} written")

    exclude = {first for first, _ in csv_hardcoded_data}

    csv_with_objects_directory = translation_build_directory / "csv_with_objects" / language.name
    csv_with_objects_directory.mkdir(parents=True, exist_ok=True)

    with_objects_csv_file_path = csv_with_objects_directory / "dfint_dictionary.csv"
    shutil.copy(hardcoded_csv_file_path, with_objects_csv_file_path)

    await asyncio.to_thread(
        process_objects,
        csv_file_path=with_objects_csv_file_path,
        language=language,
        config=config,
        exclude=exclude,
    )

    logger.info(f"{with_objects_csv_file_path.relative_to(config.working_directory)} written")


async def process_all(config: Config) -> None:
    await asyncio.gather(*(process(language, config) for language in config.languages))


app = typer.Typer()


@app.command()
def main(working_directory: Path | None) -> None:
    config = load_config(working_directory / "config.yaml")
    config.working_directory = working_directory
    asyncio.run(process_all(config))


if __name__ == "__main__":
    app()
