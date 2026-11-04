import codecs
import io
import shutil
from collections.abc import Iterable
from pathlib import Path
from typing import cast

from df_translation_toolkit.convert import objects_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from df_translation_toolkit.validation.validation_models import Diagnostics
from loguru import logger

from automation.models import Context, LanguageInfo
from automation.process_hardcoded import process_hardcoded
from automation.process_lua import process_lua, process_lua_only
from automation.process_objects import process_objects_only
from automation.process_utils import (
    check_possibility_to_encode_translations,
    get_po_file_path,
    load_po_file,
    validate_language_name,
)


def process_objects(
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

    csv_directory = csv_file_path.parent
    errors_file_path = csv_directory / "errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

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

    diagnostics = Diagnostics()
    prepared_dictionary = objects_po_to_csv.prepare_dictionary(po_data, diagnostics)
    filtered_dictionary = {source: translation for source, translation in prepared_dictionary if source not in exclude}

    if diagnostics.contains_problems():
        with errors_file_path.open("w", encoding="utf-8") as errors_file:
            errors_file.write(str(diagnostics))

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


@logger.catch(reraise=True)
def process(language: LanguageInfo, context: Context) -> None:
    validate_language_name(language.name)
    translation_build_directory = context.working_directory / "translation_build"

    csv_directory = translation_build_directory / "csv" / language.name
    shutil.rmtree(csv_directory, ignore_errors=True)
    csv_directory.mkdir(parents=True)
    hardcoded_csv_file_path = csv_directory / "dfint_dictionary.csv"

    csv_hardcoded_data = process_hardcoded(
        csv_file_path=hardcoded_csv_file_path,
        language=language,
        context=context,
        resource_name="hardcoded_steam",
    )

    logger.info(f"{hardcoded_csv_file_path.relative_to(context.working_directory)} written")

    exclude = {first for first, _ in csv_hardcoded_data}

    process_objects_only(language, context)

    csv_with_objects_directory = translation_build_directory / "csv_with_objects" / language.name
    shutil.rmtree(csv_with_objects_directory, ignore_errors=True)
    csv_with_objects_directory.mkdir(parents=True)

    with_objects_csv_file_path = csv_with_objects_directory / "dfint_dictionary.csv"
    shutil.copy(hardcoded_csv_file_path, with_objects_csv_file_path)

    csv_objects_data = process_objects(
        csv_file_path=with_objects_csv_file_path,
        language=language,
        context=context,
        exclude=exclude,
        resource_name="objects",
    )

    exclude |= {first for first, _ in csv_objects_data}

    process_lua(
        csv_file_path=with_objects_csv_file_path,
        language=language,
        context=context,
        exclude=exclude,
        resource_name="lua",
    )

    logger.info(f"{with_objects_csv_file_path.relative_to(context.working_directory)} written")
    process_lua_only(language, context)
