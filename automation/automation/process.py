import asyncio
import codecs
import io
from pathlib import Path
from typing import Optional

import aiofiles
import df_gettext_toolkit.convert.po_to_csv
import typer
import viscii_codec
from loguru import logger

from automation.load_config import load_config
from automation.models import Config, LanguageInfo

viscii_codec.register()


async def load_file(language_code: str, config: Config) -> bytes:
    source = config.source
    file_path = (
        config.working_directory
        / "translations-backup"
        / "translations"
        / source.project
        / source.resource_name
        / f"{language_code}.po"
    )

    async with aiofiles.open(file_path, "rb") as file:
        return await file.read()


async def convert(po_data: bytes, encoding: str) -> str:
    po_data = io.StringIO(po_data.decode(encoding="utf-8"))
    result = io.StringIO(newline="")
    await asyncio.to_thread(df_gettext_toolkit.convert.po_to_csv.convert, po_data, result, encoding)
    return result.getvalue()


async def process(language: LanguageInfo, config: Config):
    po_data = await load_file(language_code=language.code, config=config)
    csv_data = await convert(po_data, language.encoding)
    directory = config.working_directory / "translation_build" / language.name
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / "dfint_dictionary.csv"

    async with aiofiles.open(file_path, "wb") as csv_file:
        await csv_file.write(codecs.encode(csv_data, encoding=language.encoding))

    logger.info(f"{file_path} written")


async def process_all(config: Config):
    await asyncio.gather(*(process(language, config) for language in config.languages))


app = typer.Typer()


@app.command()
def main(working_directory: Optional[Path]):
    config = load_config(working_directory / "config.yaml")
    config.working_directory = working_directory
    asyncio.run(process_all(config))


if __name__ == "__main__":
    app()
