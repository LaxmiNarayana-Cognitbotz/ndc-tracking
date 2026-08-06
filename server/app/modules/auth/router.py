from fastapi import HTTPException
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_bearer import get_current_user
from app.dto.auth import ForgotPasswordRequest, LoginRequest, ResendOTPRequest, ResetPasswordRequest, VerifyOTPRequest
from app.modules.auth.service import AuthService
from config.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login")
async def login_post(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.authenticate_user(payload.email, payload.password, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/verify-otp")
async def verify_otp_route(payload: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.verify_otp(payload.email, payload.otp_code, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/resend-otp")
async def resend_otp_route(payload: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.resend_otp(payload.email, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        origin = request.headers.get("origin") or "http://localhost:5173"
        return await AuthService.initiate_forgot_password(payload.email, origin, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/verify-reset-token/{token}")
async def verify_reset_token(token: str, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.verify_reset_token_service(token, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await AuthService.reset_password_service(payload.token, payload.new_password, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/config")
async def get_auth_config_route():
    try:
        return AuthService.get_auth_config()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/login")
async def login(response: Response):
    try:
        sso_enabled, result = AuthService.build_sso_login_url()
        if not sso_enabled:
            return result

        # Set state cookie for CSRF protection
        response.set_cookie(key="oauth_state", value=result["state"], max_age=600, httponly=True, samesite="lax", secure=False)

        return {"url": result["url"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        cookie_state = request.cookies.get("oauth_state")

        # Clear cookie
        response.delete_cookie("oauth_state")

        base_url = str(request.base_url).rstrip('/')
        ip_address = request.client.host if request.client else None

        result = await AuthService.handle_sso_callback(code, state, cookie_state, base_url, ip_address, db)

        if result and result.get("action") == "redirect":
            return RedirectResponse(url=result["url"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/approve-access", response_class=HTMLResponse)
async def approve_access(token: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await AuthService.approve_user_access(token, db)
        return result["html"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/reject-access", response_class=HTMLResponse)
async def reject_access(token: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await AuthService.reject_user_access(token, db)
        return result["html"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        ip_address = request.client.host if request.client else None
        result = await AuthService.logout_user(auth_header, ip_address, db)
        # Append the base_url to the logout URL
        result["logout_url"] += str(request.base_url)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        email = current_user.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token session payload.")
        return await AuthService.get_current_user_info(email, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


# ==============================================================================
