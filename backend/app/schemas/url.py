from pydantic import BaseModel


class URLCreateRequest(BaseModel):
    url: str


class URLCreateResponse(BaseModel):
    short_code: str
    original_url: str
    is_reused: bool = False
    replaced_url: str | None = None
