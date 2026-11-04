import shutil

from loguru import logger

from automation.models import Context, LanguageInfo
from automation.process_hardcoded import process_hardcoded
from automation.process_lua import process_lua, process_lua_only
from automation.process_objects import process_objects, process_objects_only
from automation.process_utils import (
    temporary_csv_path,
    validate_language_name,
)


@logger.catch(reraise=True)
def process(language: LanguageInfo, context: Context) -> None:
    validate_language_name(language.name)
    translation_build_directory = context.working_directory / "translation_build"

    csv_directory = translation_build_directory / "csv" / language.name
    csv_directory.mkdir(parents=True, exist_ok=True)
    hardcoded_csv_file_path = csv_directory / "dfint_dictionary.csv"

    with temporary_csv_path(hardcoded_csv_file_path) as temporary_csv_file_path:
        csv_hardcoded_data = process_hardcoded(
            csv_file_path=temporary_csv_file_path,
            language=language,
            context=context,
            resource_name="hardcoded_steam",
        )

    logger.info(f"{hardcoded_csv_file_path.relative_to(context.working_directory)} written")

    exclude = {first for first, _ in csv_hardcoded_data}

    process_objects_only(language, context)

    csv_with_objects_directory = translation_build_directory / "csv_with_objects" / language.name
    csv_with_objects_directory.mkdir(parents=True, exist_ok=True)

    with_objects_csv_file_path = csv_with_objects_directory / "dfint_dictionary.csv"
    with temporary_csv_path(with_objects_csv_file_path) as temporary_csv_file_path:
        if hardcoded_csv_file_path.exists():
            shutil.copy(hardcoded_csv_file_path, temporary_csv_file_path)

        csv_objects_data = process_objects(
            csv_file_path=temporary_csv_file_path,
            language=language,
            context=context,
            exclude=exclude,
            resource_name="objects",
        )

        exclude |= {first for first, _ in csv_objects_data}

        process_lua(
            csv_file_path=temporary_csv_file_path,
            language=language,
            context=context,
            exclude=exclude,
            resource_name="lua",
        )

    logger.info(f"{with_objects_csv_file_path.relative_to(context.working_directory)} written")
    process_lua_only(language, context)
