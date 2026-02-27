"""
Auth Endpoint

POST /api/v1/auth/login  →  returns a JWT access token for the supervisor.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import create_access_token, verify_password

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Supervisor login",
    description="Returns a JWT access token. Use it as `Authorization: Bearer <token>`.",
)
@limiter.limit("5/minute")
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    valid_username = form.username == settings.SUPERVISOR_USERNAME
    valid_password = verify_password(form.password, settings.SUPERVISOR_PASSWORD_HASH)

    if not valid_username or not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=form.username)
    return TokenResponse(access_token=token)
