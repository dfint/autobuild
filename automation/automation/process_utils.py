import codecs
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from babel.messages.pofile import read_po
from df_translation_toolkit.utils.po_utils import simple_read_po

from automation.models import LanguageInfo


def validate_language_name(language_name: str) -> None:
    if (
        not language_name
        or language_name in {".", ".."}
        or Path(language_name).name != language_name
        or "\\" in language_name
    ):
        error_message = "language_name must be a single path component"
        raise ValueError(error_message)


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


def load_po_file_with_context(file_path: Path) -> list[tuple[str, str, str]]:
    with file_path.open(encoding="utf-8") as file:
        return [
            (str(item.id), str(item.context or ""), str(item.string))
            for item in read_po(file)
            if item.id and item.string
        ]


@contextmanager
def temporary_csv_path(csv_file_path: Path) -> Generator[Path, None, None]:
    csv_file_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        dir=csv_file_path.parent,
        prefix=f".{csv_file_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_csv_file_path = Path(temporary_file.name)

    try:
        yield temporary_csv_file_path
        if temporary_csv_file_path.stat().st_size > 0:
            temporary_csv_file_path.replace(csv_file_path)
    finally:
        temporary_csv_file_path.unlink(missing_ok=True)


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
