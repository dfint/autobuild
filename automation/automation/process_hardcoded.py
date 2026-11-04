import codecs
import io
from collections.abc import Iterable
from pathlib import Path
from typing import cast

import alternative_encodings
from df_translation_toolkit.convert import hardcoded_po_to_csv
from df_translation_toolkit.utils.csv_utils import writer
from loguru import logger

from automation.models import Context, LanguageInfo
from automation.process_utils import check_possibility_to_encode_translations, get_po_file_path, load_po_file

alternative_encodings.register_all()


def process_hardcoded(
    *,
    csv_file_path: Path,
    language: LanguageInfo,
    context: Context,
    resource_name: str,
) -> Iterable[tuple[str, str]]:
    logger.info(f"Processing {resource_name} resource")
    po_file_path = get_po_file_path(
        working_directory=context.working_directory,
        project_name=context.config.source.project,
        resource_name=resource_name,
        language_code=language.code,
    )
    po_data = load_po_file(file_path=po_file_path)
    prepared_dictionary = list(hardcoded_po_to_csv.prepare_dictionary(po_data))
    if not prepared_dictionary:
        logger.warning(f"Empty {resource_name} resource, skipping.")
        return []

    check_possibility_to_encode_translations(prepared_dictionary, language, resource_name)

    logger.info(f"Processed lines: {len(prepared_dictionary)=}")

    csv_data_buffer = io.StringIO(newline="")
    csv_writer = writer(csv_data_buffer)
    csv_writer.writerows(cast("Iterable[list[str]]", prepared_dictionary))
    csv_data_buffer.flush()
    csv_data_buffer.seek(0)

    with csv_file_path.open("wb") as csv_file:
        data = csv_data_buffer.read()
        csv_file.write(codecs.encode(data, encoding=language.encoding))
        logger.info(f"Written data size: {len(data)=}")
        assert len(data) > 0

    return prepared_dictionary
