from pydantic import BaseModel, HttpUrl


class CreateTrackTaskFromUrlRequest(BaseModel):
    file_url: HttpUrl
    lang_code: str
