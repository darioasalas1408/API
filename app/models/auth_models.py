from typing import Literal
from pydantic import BaseModel

Role = Literal["admin", "user"]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    ok: bool = True
    role: Role


class MeResponse(BaseModel):
    email: str
    full_name: str
    role: Role
    id: str
