from pydantic import BaseModel


class OpenAIBriefProseResponse(BaseModel):
    rewritten: str = ""
