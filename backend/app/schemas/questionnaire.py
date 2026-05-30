from pydantic import BaseModel


class QuestionnaireSubmit(BaseModel):
    personality: dict
    voice: dict
    values: dict
    knowledge: dict
    limits: dict


class QuestionnaireResponse(BaseModel):
    profile_id: str
    version: int
    trait_count: int
    has_writing_sample: bool
