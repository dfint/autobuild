import codecs
from collections.abc import Iterable
from pathlib import Path

from automation.models import LanguageInfo


def get_po_file_path(*, working_directory: Path, project_name: str, resource_name: str, language_code: str) -> Path:
    return (
        working_directory
        / "translations-backup"
        / "translations"
        / project_name
        / resource_name
        / f"{language_code}.po"
    )


def check_possibility_to_encode_translations(
    dictionary: Iterable[tuple[str, str]],
    language: LanguageInfo,
    resource_name: str,
) -> None:
    for original, translation in dictionary:
        try:
            codecs.encode(translation, encoding=language.encoding)
        except UnicodeEncodeError as ex:
            msg = f"Error trying encode translation: {translation!r}; original: {original!r}, resource: {resource_name}"
            raise ValueError(msg) from ex
