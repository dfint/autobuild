from pydantic import BaseModel


class LanguageInfo(BaseModel):
    name: str
    code: str
    encoding: str


class Config(BaseModel):
    languages: list[LanguageInfo]
