from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests
import typer
from babel.messages.pofile import read_po
from langcodes import Language
from loguru import logger
from scour.scour import scourString as scour_string


def translated_lines(path: Path) -> tuple[int, set[str], set[str]]:
    entries: int = 0
    translated_entries: set[tuple[str, str]] = set()
    notranslated_entries: set[tuple[str, str]] = set()

    with path.open(encoding="utf-8") as file:
        catalog = read_po(file)
        for message in catalog:
            if message.id:
                entries += 1
                if message.string:
                    if message.string != message.id:
                        translated_entries.add((message.context, message.id))
                    else:
                        notranslated_entries.add((message.context, message.id))

    return entries, translated_entries, notranslated_entries


def resource_stat(path: Path) -> tuple[dict[str, int], int]:
    path = Path(path)
    output: dict[str, int] = {}
    total_lines: int = 0
    all_translated: set[tuple[str, str]] = set()
    all_notranslated: set[tuple[str, str]] = set()

    for file in sorted(filter(Path.is_file, path.glob("*.po"))):
        language = Language.get(file.stem).display_name()
        total_lines, translated_entries, notranslated_entries = translated_lines(file)
        translated_count = len(translated_entries)
        output[language] = translated_count
        logger.debug(f"{language}: {translated_count}")

        all_translated.update(translated_entries)
        all_notranslated.update(notranslated_entries)

    # Estimate number of lines with "notranslate" tag on transifex
    notranslate_count = len(notranslated_entries - translated_entries)

    return output, total_lines - notranslate_count


def prepare_chart_data(data: dict[str, dict[str, float]], labels: list[str], max_lines: int) -> dict[str, Any]:
    datasets = [
        dict(
            label=resource,
            data=[lines[label] for label in labels],
        )
        for resource, lines in data.items()
    ]

    return dict(
        type="horizontalBar",
        data=dict(labels=labels, datasets=datasets),
        options=dict(
            scales=dict(
                yAxes=[dict(stacked=True)],
                xAxes=[
                    dict(
                        stacked=True,
                        ticks=dict(
                            beginAtZero=True,
                            max=max_lines,
                            stepSize=10000,
                        ),
                    )
                ],
            ),
        ),
    )


def get_chart(chart_data: dict[str, Any], file_format: str = "png", width: int = 800, height: int = 800) -> bytes:
    url = "https://quickchart.io/chart"
    payload = dict(
        width=width,
        height=height,
        backgroundColor="rgb(255, 255, 255)",
        format=file_format,
        chart=chart_data,
    )

    headers = {"Content-type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    return response.content


def prepare_dataset(path: Path):
    dataset: dict[str, dict[str, float]] = {}
    total_lines: int = 0
    languages: set[str] = set()

    for resource_directory in sorted(filter(Path.is_dir, path.glob("*"))):
        logger.info(f"processing directory: {resource_directory}")
        resource_stats, resource_total_lines = resource_stat(resource_directory)
        dataset[resource_directory.name] = resource_stats
        logger.info(f"{resource_total_lines=}")
        total_lines += resource_total_lines
        languages.update(resource_stats.keys())

    return dataset, languages, total_lines


def minify_svg(data: bytes) -> bytes:
    return scour_string(data.decode("utf-8"), options=SimpleNamespace(strip_ids=True, shorten_ids=True)).encode("utf-8")


app = typer.Typer()


@app.command()
def generate_chart(source_dir: Path, output: Path, minimal_percent: int = 0, width: int = 800, height: int = 800):
    logger.info(f"source_dir: {source_dir.resolve()}")
    assert source_dir.resolve().exists()
    logger.info(f"output: {output.resolve()}")
    output.parent.mkdir(exist_ok=True, parents=True)

    dataset, languages, total_lines = prepare_dataset(source_dir)
    count_by_language = {language: sum(item[language] for item in dataset.values()) for language in languages}

    if minimal_percent:
        languages = [
            language for language in languages if count_by_language[language] / total_lines > minimal_percent / 100
        ]

    languages = sorted(languages, key=lambda language: (-count_by_language[language], language))
    logger.info(f"resources={list(dataset.keys())}")
    logger.info(f"{languages=}")
    logger.info(f"{total_lines=}")
    assert total_lines, "Empty result"

    chart_data = prepare_chart_data(dataset, languages, total_lines)
    file_format = output.suffix[1:]
    chart = get_chart(chart_data, file_format=file_format, width=width, height=height)

    if file_format == "svg":
        chart = minify_svg(chart)

    output.write_bytes(chart)
    logger.info(f"{output.name} chart file is saved")
