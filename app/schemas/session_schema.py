from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    user_id: int
    title: str
    created_at: str
