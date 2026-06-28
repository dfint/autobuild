import typer
from models import Config, Context, LanguageInfo, SourceInfo
from process import process
from pathlib import Path

app = typer.Typer()


@app.command()
def main(working_directory: Path, language_name: str, language_code: str, encoding: str, project: str="dwarf-fortress-steam") -> None:
    context = Context(
        config=Config(source=SourceInfo(project=project)),
        working_directory=working_directory,
    )

    language_info = LanguageInfo(
        name=language_name,
        code=language_code,
        encoding=encoding,
    )
    process(language_info, context)


if __name__ == "__main__":
    app()
