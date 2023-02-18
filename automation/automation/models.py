from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class LanguageInfo(BaseModel):
    name: str
    code: str
    encoding: str


class Config(BaseModel):
    working_directory: Optional[Path]
    languages: list[LanguageInfo]
