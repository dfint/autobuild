from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class LanguageInfo(BaseModel):
    name: str
    code: str
    encoding: str


class SourceInfo(BaseModel):
    base_url: str
    project: str
    resource_name: str


class Config(BaseModel):
    source: SourceInfo
    working_directory: Optional[Path] = None
    languages: list[LanguageInfo]
