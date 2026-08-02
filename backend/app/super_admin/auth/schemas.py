from pydantic import BaseModel, ConfigDict, EmailStr


class SuperAdminLogin(BaseModel):
    email: EmailStr
    password: str


class SuperAdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SuperAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None = None


class SuperAdminMessage(BaseModel):
    message: str
