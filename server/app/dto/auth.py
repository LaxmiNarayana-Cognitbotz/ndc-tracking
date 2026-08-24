from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str


class ResendOTPRequest(BaseModel):
    email: str


class UserCreateRequest(BaseModel):
    email: str
    name: str
    role: str
    password: str


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = None
