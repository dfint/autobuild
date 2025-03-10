from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NamedTuple, NewType

import requests
import typer
from babel.messages.pofile import read_po
from langcodes import Language
from loguru import logger
from scour.scour import scourString as scour_string  # noqa: N813
from tqdm import tqdm

DEFAULT_WIDTH = 600
DEFAULT_LINE_HEIGHT = 14


LanguageName = NewType("LanguageName", str)
ResourceName = NewType("ResourceName", str)


class StringWithContext(NamedTuple):
    string: str
    context: str | None


class CountTranslatedLinesResult(NamedTuple):
    total_lines_count: int
    translated_entries: set[StringWithContext]
    notranslated_entries: set[StringWithContext]


@dataclass
class Dataset:
    data: dict[ResourceName, dict[LanguageName, float]]
    languages: list[LanguageName]
    total_lines: int

    @property
    def resources(self) -> list[ResourceName]:
        return list(self.data.keys())

    def with_languages(self, languages: list[LanguageName]) -> "Dataset":
        return Dataset(data=self.data, languages=languages, total_lines=self.total_lines)

    def get_count_by_languages(self) -> dict[LanguageName, int]:
        return {language: sum(item[language] for item in self.data.values()) for language in self.languages}

    def sort_languages(self) -> None:
        count_by_language = self.get_count_by_languages()
        self.languages = sorted(self.languages, key=lambda language: (-count_by_language[language], language))

    def with_minimal_translation_percent(self, minimal_percent: float) -> "Dataset":
        languages = filter_languages_by_minmal_translation_count(
            languages=self.languages,
            count_by_language=self.get_count_by_languages(),
            minimal_count=minimal_percent / 100 * self.total_lines,
        )
        return self.with_languages(languages)


def translated_lines(path: Path) -> CountTranslatedLinesResult:
    entries: int = 0
    translated_entries: set[StringWithContext] = set()
    notranslated_entries: set[StringWithContext] = set()

    with path.open(encoding="utf-8") as file:
        catalog = read_po(file)
        for message in catalog:
            if message.id:
                entries += 1
                if message.string:
                    if message.string != message.id:
                        translated_entries.add(StringWithContext(message.id, message.context))
                    else:
                        notranslated_entries.add(StringWithContext(message.id, message.context))

    return CountTranslatedLinesResult(entries, translated_entries, notranslated_entries)


def resource_stat(path: Path) -> tuple[dict[LanguageName, int], int]:
    path = Path(path)
    output: dict[LanguageName, int] = {}
    total_lines: int = 0
    all_translated: set[StringWithContext] = set()
    all_notranslated: set[StringWithContext] = set()

    for file in tqdm(sorted(filter(Path.is_file, path.glob("*.po"))), leave=False):
        language = LanguageName(Language.get(file.stem).display_name())
        result = translated_lines(file)
        translated_count = len(result.translated_entries)
        output[language] = translated_count

        total_lines = max(total_lines, result.total_lines_count)
        all_translated.update(result.translated_entries)
        all_notranslated.update(result.notranslated_entries)

    # Estimate number of lines with "notranslate" tag on transifex
    notranslate_count = len(all_notranslated - all_translated)

    return output, total_lines - notranslate_count


def prepare_chart_data(dataset: Dataset) -> dict[str, Any]:
    datasets = [
        dict(
            label=resource,
            data=[lines[label] for label in dataset.languages],
        )
        for resource, lines in dataset.data.items()
    ]

    return dict(
        type="horizontalBar",
        data=dict(labels=dataset.languages, datasets=datasets),
        options=dict(
            scales=dict(
                yAxes=[dict(stacked=True)],
                xAxes=[
                    dict(
                        stacked=True,
                        ticks=dict(
                            beginAtZero=True,
                            max=dataset.total_lines,
                            stepSize=10000,
                        ),
                    ),
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


def prepare_dataset(path: Path) -> Dataset:
    data: dict[ResourceName, dict[LanguageName, float]] = {}
    total_lines: int = 0
    languages: set[LanguageName] = set()

    for resource_directory in sorted(filter(Path.is_dir, path.glob("*"))):
        logger.info(f"processing directory: {resource_directory}")
        resource_stats, resource_total_lines = resource_stat(resource_directory)
        data[ResourceName(resource_directory.name)] = resource_stats
        logger.info(f"{resource_total_lines=}")
        total_lines += resource_total_lines
        languages.update(resource_stats.keys())

    return Dataset(data=data, languages=languages, total_lines=total_lines)


def minify_svg(data: bytes) -> bytes:
    return scour_string(data.decode("utf-8"), options=SimpleNamespace(strip_ids=True, shorten_ids=True)).encode("utf-8")


def filter_languages_by_minmal_translation_count(
    languages: Iterable[LanguageName],
    count_by_language: dict[LanguageName, int],
    minimal_count: int,
) -> list[LanguageName]:
    return [language for language in languages if count_by_language[language] > minimal_count]


def generate_diagram(
    dataset: Dataset,
    width: int,
    height: int,
    output: Path,
) -> None:
    chart_data = prepare_chart_data(dataset)
    file_format = output.suffix[1:]
    chart = get_chart(chart_data, file_format=file_format, width=width, height=height)

    if file_format == "svg":
        chart = minify_svg(chart)

    output.write_bytes(chart)
    logger.info(f"{output.name} chart file is saved")


app = typer.Typer()


@app.command(name="generate")
def command_generate(
    source_dir: Path,
    output: Path,
    minimal_percent: int = 0,
    width: int = DEFAULT_WIDTH,
    height: int | None = None,
) -> None:
    logger.info(f"source_dir: {source_dir.resolve()}")
    assert source_dir.resolve().exists()
    logger.info(f"output: {output.resolve()}")
    output.parent.mkdir(exist_ok=True, parents=True)

    dataset: Dataset = prepare_dataset(source_dir)
    count_by_language = dataset.get_count_by_languages()

    logger.info(f"{dataset.resources=}")
    logger.info(f"{dataset.languages=}")
    logger.info(f"{dataset.total_lines=}")

    if minimal_percent:
        dataset = dataset.with_minimal_translation_percent(minimal_percent)

    dataset.sort_languages()

    for language in dataset.languages:
        logger.info(f"{language}: {count_by_language[language] / dataset.total_lines * 100:.1f}%")

    height = height or (len(dataset.languages) + 6) * DEFAULT_LINE_HEIGHT
    generate_diagram(dataset, width, height, output)


@app.command(name="two_diagrams")
def command_two_diagrams(
    source_dir: Path,
    output_dir: Path,
) -> None:
    logger.info(f"source_dir: {source_dir.resolve()}")
    assert source_dir.resolve().exists()
    logger.info(f"output_dir: {output_dir.resolve()}")
    output_dir.mkdir(exist_ok=True, parents=True)

    dataset: Dataset = prepare_dataset(source_dir)
    count_by_language = dataset.get_count_by_languages()

    logger.info(f"{dataset.resources=}")
    logger.info(f"{dataset.languages=}")
    logger.info(f"{dataset.total_lines=}")

    dataset.sort_languages()

    for language in dataset.languages:
        logger.info(f"{language}: {count_by_language[language] / dataset.total_lines * 100:.1f}%")

    width = DEFAULT_WIDTH
    height = (len(dataset.languages) + 6) * DEFAULT_LINE_HEIGHT
    generate_diagram(dataset, width, height, output_dir / "dwarf-fortress-steam.svg")

    dataset = dataset.with_minimal_translation_percent(1)
    height = (len(dataset.languages) + 6) * DEFAULT_LINE_HEIGHT
    generate_diagram(dataset, width, height, output_dir / "dwarf-fortress-steam-short.svg")
