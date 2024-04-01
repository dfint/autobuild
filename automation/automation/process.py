import asyncio
import codecs
import io
from pathlib import Path
from typing import Optional

import aiofiles
import df_translation_toolkit.convert.hardcoded_po_to_csv
import df_translation_toolkit.convert.objects_po_to_csv
import typer
from alternative_encodings import cp859, cp866i, viscii
from loguru import logger

from automation.load_config import load_config
from automation.models import Config, LanguageInfo

cp859.register()
cp866i.register()
viscii.register()

async def load_file(language_code: str, resource_name: str, config: Config) -> bytes:
    source = config.source
    file_path = (
        config.working_directory
        / "translations-backup"
        / "translations"
        / source.project
        / resource_name
        / f"{language_code}.po"
    )

    async with aiofiles.open(file_path, "rb") as file:
        return await file.read()


async def convert_hardcoded(po_data: bytes) -> str:
    po_data = io.StringIO(po_data.decode(encoding="utf-8"))
    result = io.StringIO(newline="")
    await asyncio.to_thread(df_translation_toolkit.convert.hardcoded_po_to_csv.convert, po_data, result)
    return result.getvalue()


async def convert_objects(po_data: bytes, errors_file) -> str:
    po_data = io.StringIO(po_data.decode(encoding="utf-8"))
    result = io.StringIO(newline="")
    await asyncio.to_thread(df_translation_toolkit.convert.objects_po_to_csv.convert, po_data, result, errors_file)
    return result.getvalue()


@logger.catch(reraise=True)
async def process(language: LanguageInfo, config: Config):
    csv_directory = config.working_directory / "translation_build" / "csv" / language.name
    csv_directory.mkdir(parents=True, exist_ok=True)

    po_data = await load_file(language_code=language.code, resource_name="hardcoded_steam", config=config)
    csv_data = await convert_hardcoded(po_data)
    file_path = csv_directory / "dfint_dictionary.csv"
    async with aiofiles.open(file_path, "wb") as csv_file:
        await csv_file.write(codecs.encode(csv_data, encoding=language.encoding))

    logger.info(f"{file_path} written")

    csv_with_objects_directory = config.working_directory / "translation_build" / "csv_with_objects" / language.name
    csv_with_objects_directory.mkdir(parents=True, exist_ok=True)

    errors_file_path = csv_with_objects_directory / "errors.txt"
    if errors_file_path.exists():
        errors_file_path.unlink()

    po_data = await load_file(language_code=language.code, resource_name="objects", config=config)

    with errors_file_path.open("w", encoding="utf-8") as errors_file:
        csv_with_objects_data = await convert_objects(po_data, errors_file)

    if errors_file_path.stat().st_size == 0:
        errors_file_path.unlink()

    file_path = csv_with_objects_directory / "dfint_dictionary.csv"
    async with aiofiles.open(file_path, "wb") as csv_file:
        await csv_file.write(codecs.encode(csv_data, encoding=language.encoding))
        await csv_file.write(codecs.encode(csv_with_objects_data, encoding=language.encoding))


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
