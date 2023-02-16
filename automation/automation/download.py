import asyncio
import io
from pathlib import Path
from pprint import pformat

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
    result = io.StringIO()
    await asyncio.to_thread(df_gettext_toolkit.convert.po_to_csv.convert, po_data, result, encoding)
    return result.getvalue()


async def process(language: LanguageInfo):
    po_data = await fetch(language_code=language.code)
    csv_data = await convert(po_data, language.encoding)
    ...  # TODO: write into a file


async def fetch_all(languages: list[LanguageInfo]):
    results = await asyncio.gather(*(process(language) for language in languages))
    logger.debug(pformat([x.decode("utf-8")[:20] for x in results]))


def main(config: Path):
    config = load_config(config)
    asyncio.run(fetch_all(config.languages))


if __name__ == "__main__":
    typer.run(main)
