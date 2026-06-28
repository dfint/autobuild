from pathlib import Path

from pydantic import BaseModel, Field


class LanguageInfo(BaseModel):
    name: str
    code: str
    encoding: str


class SourceInfo(BaseModel):
    project: str = ""


class Config(BaseModel):
    source: SourceInfo
    languages: list[LanguageInfo] = Field(default_factory=list)


class Context(BaseModel):
    config: Config
    working_directory: Path
