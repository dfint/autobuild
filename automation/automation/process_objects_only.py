import codecs
import io
import shutil
from pathlib import Path

import alternative_encodings
import typer
from babel.messages.pofile import read_po
from df_translation_toolkit.convert import objects_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from df_translation_toolkit.validation.validation_models import Diagnostics
from loguru import logger

from automation.models import Config, Context, LanguageInfo, SourceInfo
from automation.process_utils import check_possibility_to_encode_translations, get_po_file_path

alternative_encodings.register_all()


def load_po_file_with_context(file_path: Path) -> list[tuple[str, str, str]]:
    with file_path.open(encoding="utf-8") as file:
        return [
            (str(item.id), str(item.context or ""), str(item.string))
            for item in read_po(file)
            if item.id and item.string
        ]


def process_objects_with_context(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    context: Context,
    resource_name: str,
) -> None:
    logger.info(f"Processing {resource_name} resource with context")
    errors_file_path = csv_file_path.parent / "errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

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

    diagnostics = Diagnostics()
    filtered_dictionary: dict[tuple[str, str], str] = {}
    for original, object_context, translation in po_data:
        prepared_entries = objects_po_to_csv.prepare_dictionary([(original, translation)], diagnostics)
        for source, prepared_translation in prepared_entries:
            filtered_dictionary[source, object_context] = prepared_translation

    if diagnostics.contains_problems():
        with errors_file_path.open("w", encoding="utf-8") as errors_file:
            errors_file.write(str(diagnostics))

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


def process_objects_only(language: LanguageInfo, context: Context) -> None:
    translation_build_directory = context.working_directory / "translation_build"
    csv_objects_directory = translation_build_directory / "csv_objects" / language.name
    shutil.rmtree(csv_objects_directory, ignore_errors=True)
    csv_objects_directory.mkdir(parents=True)
    objects_csv_file_path = csv_objects_directory / "dfint_dictionary.csv"
    process_objects_with_context(
        csv_file_path=objects_csv_file_path,
        language=language,
        context=context,
        resource_name="objects",
    )
    logger.info(f"{objects_csv_file_path.relative_to(context.working_directory)} written")

app = typer.Typer()


@app.command()
def main(
    working_directory: Path,
    language_name: str,
    language_code: str,
    encoding: str,
    project: str = "dwarf-fortress-steam",
) -> None:
    context = Context(
        config=Config(source=SourceInfo(project=project), languages=[]),
        working_directory=working_directory,
    )

    language_info = LanguageInfo(
        name=language_name,
        code=language_code,
        encoding=encoding,
    )
    process_objects_only(language_info, context)


if __name__ == "__main__":
    app()
