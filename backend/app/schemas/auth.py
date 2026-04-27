import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]
    nickname: Annotated[str, StringConstraints(pattern=r"^[A-Za-z]+$", min_length=1, max_length=32)] | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nickname: str
    avatar_url: str | None = None


class ErrorResponse(BaseModel):
    detail: str
