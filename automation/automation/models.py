from pathlib import Path

from pydantic import BaseModel


class LanguageInfo(BaseModel):
    name: str
    code: str
    encoding: str


class SourceInfo(BaseModel):
    project: str


class Config(BaseModel):
    source: SourceInfo
    working_directory: Path | None = None
    languages: list[LanguageInfo]
