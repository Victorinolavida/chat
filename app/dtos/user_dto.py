from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateDTO(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserLoginDTO(BaseModel):
    email: EmailStr
    password: str


class UserReadDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class UserPublicDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
