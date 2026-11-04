import codecs
import io
import shutil
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import cast

import alternative_encodings
import typer
from df_translation_toolkit.convert import hardcoded_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from loguru import logger

from automation.models import Config, Context, LanguageInfo, SourceInfo
from automation.process_utils import (
    check_possibility_to_encode_translations,
    get_po_file_path,
    load_po_file,
    load_po_file_with_context,
    validate_language_name,
)

alternative_encodings.register_all()


def prepare_lua_string(source_string: str, translation: str) -> Iterator[tuple[str, str]]:
    source_string = source_string.rstrip("]")
    translation = translation.rstrip("]")
    source_parts = source_string.split(":")
    translation_parts = translation.split(":")
    if len(source_parts) != len(translation_parts):
        yield source_string, translation
        return

    yield from zip(source_parts, translation_parts, strict=True)


def process_lua_strings(prepared_dictionary: Iterable[tuple[str, str]]) -> Iterable[tuple[str, str]]:
    for source, translation in prepared_dictionary:
        yield from prepare_lua_string(source, translation)


def process_lua(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    context: Context,
    exclude: set[str] | None = None,
    resource_name: str,
) -> Iterable[tuple[str, str]]:
    logger.info(f"Processing {resource_name} resource")
    if not exclude:
        exclude = set()

    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name=resource_name,
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    po_data = [(source, translation) for source, translation in po_data if source not in exclude]
    if not po_data:
        logger.warning(f"Empty {resource_name} resource, skipping.")
        return []

    prepared_dictionary = process_lua_strings(hardcoded_po_to_csv.prepare_dictionary(po_data))
    filtered_dictionary = {source: translation for source, translation in prepared_dictionary if source not in exclude}
    if not filtered_dictionary:
        logger.warning(f"Empty filtered dictionary from {resource_name} resource, skipping.")
        return []

    logger.info(f"Filtered lines: {len(filtered_dictionary)=}")
    check_possibility_to_encode_translations(filtered_dictionary.items(), language, resource_name)

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(cast("Iterable[list[str]]", filtered_dictionary.items()))
    csv_data_buffer.flush()
    csv_data_buffer.seek(0)

    with csv_file_path.open("ab") as csv_file:
        data = csv_data_buffer.read()
        csv_file.write(codecs.encode(data, encoding=language.encoding))
        logger.info(f"Written data size: {len(data)=}")
        assert len(data) > 0

    return filtered_dictionary.items()


def process_lua_with_context(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    context: Context,
    resource_name: str,
) -> None:
    logger.info(f"Processing {resource_name} resource with context")
    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name=resource_name,
        language_code=language.code,
    )
    po_data = load_po_file_with_context(file_path=po_file_path)
    if not po_data:
        logger.warning(f"Empty {resource_name} resource, skipping.")
        return

    filtered_dictionary: dict[tuple[str, str], str] = {}
    for original, object_context, translation in po_data:
        prepared_entries = hardcoded_po_to_csv.prepare_dictionary([(original, translation)])
        for source, prepared_translation in process_lua_strings(prepared_entries):
            filtered_dictionary[source, object_context] = prepared_translation

    if not filtered_dictionary:
        logger.warning(f"Empty filtered dictionary from {resource_name} resource, skipping.")
        return

    logger.info(f"Filtered lines: {len(filtered_dictionary)=}")
    check_possibility_to_encode_translations(
        ((source, translation) for (source, _), translation in filtered_dictionary.items()),
        language,
        resource_name,
    )

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    rows = [
        [source, object_context, translation]
        for (source, object_context), translation in filtered_dictionary.items()
    ]
    csv_writer.writerows(rows)
    csv_data_buffer.flush()
    csv_data_buffer.seek(0)

    with csv_file_path.open("wb") as csv_file:
        data = csv_data_buffer.read()
        csv_file.write(codecs.encode(data, encoding=language.encoding))
        logger.info(f"Written data size: {len(data)=}")
        assert len(data) > 0


def process_lua_only(language: LanguageInfo, context: Context) -> None:
    validate_language_name(language.name)
    translation_build_directory = context.working_directory / "translation_build"
    csv_lua_directory = translation_build_directory / "csv_lua" / language.name
    shutil.rmtree(csv_lua_directory, ignore_errors=True)
    csv_lua_directory.mkdir(parents=True)
    lua_csv_file_path = csv_lua_directory / "dfint_dictionary.csv"
    process_lua_with_context(
        csv_file_path=lua_csv_file_path,
        language=language,
        context=context,
        resource_name="lua",
    )
    logger.info(f"{lua_csv_file_path.relative_to(context.working_directory)} written")


app = typer.Typer()


@app.command()
def main(
    working_directory: Path,
    language_name: str,
    language_code: str,
    encoding: str,
    project: str = "dwarf-fortress-steam",
) -> None:
    try:
        validate_language_name(language_name)
    except ValueError as ex:
        raise typer.BadParameter(str(ex)) from ex

    context = Context(
        config=Config(source=SourceInfo(project=project), languages=[]),
        working_directory=working_directory,
    )
    language_info = LanguageInfo(name=language_name, code=language_code, encoding=encoding)
    process_lua_only(language_info, context)


if __name__ == "__main__":
    app()
