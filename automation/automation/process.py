import asyncio
import io
from pathlib import Path
from typing import Optional

import df_gettext_toolkit.convert.po_to_csv
import httpx
import typer
from loguru import logger

from automation.load_config import load_config
from automation.models import LanguageInfo

base_url = "https://github.com/dfint/translations-backup/raw/main/translations/"
project = "dwarf-fortress-steam"
resource_name = "hardcoded_steam"


async def fetch(language_code: str) -> bytes:
    async with httpx.AsyncClient() as client:
        url = base_url + f"{project}/{resource_name}/{language_code}.po"
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content


async def convert(po_data: bytes, encoding: str) -> str:
    po_data = io.StringIO(po_data.decode(encoding="utf-8"))
    result = io.StringIO(newline="")
    await asyncio.to_thread(df_gettext_toolkit.convert.po_to_csv.convert, po_data, result, encoding)
    return result.getvalue()


async def process(working_directory: Path, language: LanguageInfo):
    po_data = await fetch(language_code=language.code)
    csv_data = await convert(po_data, language.encoding)
    directory = working_directory / "translation_build" / language.name
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / "dfint_dictionary.csv"

    with open(file_path, "w", encoding=language.encoding) as csv_file:
        csv_file.write(csv_data)

    logger.info(f"{file_path} written")


async def process_all(working_directory: Path, languages: list[LanguageInfo]):
    await asyncio.gather(*(process(working_directory, language) for language in languages))


app = typer.Typer()


@app.command()
def main(working_directory: Optional[Path]):
    config = load_config(working_directory / "config.yaml")
    asyncio.run(process_all(working_directory, config.languages))


if __name__ == "__main__":
    app()
