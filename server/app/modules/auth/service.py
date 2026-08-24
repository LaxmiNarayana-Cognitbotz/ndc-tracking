import asyncio
import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import create_access_token, decode_jwt_token
from app.models.ndc_auth_audit_log import NdcAuthAuditLog
from app.models.ndc_user_access import NdcUserAccess
from app.utils.password import hash_password, verify_password

logger = logging.getLogger(__name__)

# Global keys cache for Azure AD
_azure_keys_cache = {}


# ── Helper: Send email via SMTP ──────────────────────────────────────────────


class AuthService:
    @staticmethod
    async def send_auth_email(to_email: str, subject: str, body_html: str) -> bool:
        try:
            smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_from:
                logger.error("SMTP_FROM not configured in env")
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html"))

            try:
                def _send():
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                        server.ehlo()
                        if "starttls" in server.esmtp_features:
                            server.starttls()
                            server.ehlo()
                        if smtp_password:
                            server.login(smtp_user, smtp_password)
                        server.sendmail(smtp_from, [to_email], msg.as_string())
            
                await asyncio.to_thread(_send)
                logger.info(f"Auth email sent successfully to {to_email}")
                return True
            except Exception as e:
                logger.error(f"Failed to send auth email to {to_email}: {e}")
                return False
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_auth_email: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    # ── Helper: Verify ID Token signature using Azure JWKS ───────────────────────

    @staticmethod
    async def verify_azure_token(token: str, tenant_id: str, client_id: str) -> dict:
        try:
            global _azure_keys_cache
            if not _azure_keys_cache:
                url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
                async with httpx.AsyncClient() as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        _azure_keys_cache = r.json()
                    else:
                        raise HTTPException(status_code=500, detail="Failed to fetch Azure AD keys")

            try:
                unverified_header = jwt.get_unverified_header(token)
            except JWTError as e:
                raise HTTPException(status_code=401, detail=f"Invalid token format: {str(e)}")

            kid = unverified_header.get("kid")
            if not kid:
                raise HTTPException(status_code=401, detail="Token header is missing 'kid'")

            rsa_key = None
            for key in _azure_keys_cache.get("keys", []):
                if key.get("kid") == kid:
                    rsa_key = key
                    break

            if not rsa_key:
                # Refetch keys in case of rotation
                url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
                async with httpx.AsyncClient() as client:
                    r = await client.get(url)
                    if r.status_code == 200:
                        _azure_keys_cache = r.json()
                for key in _azure_keys_cache.get("keys", []):
                    if key.get("kid") == kid:
                        rsa_key = key
                        break

            if not rsa_key:
                raise HTTPException(status_code=401, detail="No matching public key found for token verification")

            try:
                # Validate audience and decrypt/verify signature. Disable strict issuer validation to handle multiple potential formats.
                payload = jwt.decode(token, rsa_key, algorithms=["RS256"], audience=client_id, options={"verify_iss": False})
                return payload
            except JWTError as e:
                raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in verify_azure_token: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    # ── Helper: Get super admin list from env ─────────────────────────────────────

    @staticmethod
    def _get_super_admins() -> list[str]:
        try:
            super_admin_env = os.getenv("SUPER_ADMIN_EMAIL", "")
            return [e.strip().lower() for e in super_admin_env.split(",") if e.strip()]
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in _get_super_admins: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    # ── Auth Service Functions ────────────────────────────────────────────────────

    @staticmethod
    async def authenticate_user(email: str, password: str, db: AsyncSession) -> dict:
        """Authenticate user with email/password and send OTP to email."""
        try:
            email = email.strip().lower()

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

            if user_access.status == "pending":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your access request is pending approval.")

            if user_access.status == "rejected":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Your request has been rejected.")

            if not user_access.hashed_password or not verify_password(password, user_access.hashed_password):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

            # Generate 6-digit OTP
            otp_code = f"{secrets.randbelow(900000) + 100000}"
            user_access.otp_code = otp_code
            user_access.otp_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
            await db.commit()

            # Send OTP email
            body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #003b70; margin-bottom: 16px;">NDC Tracking System - Login Verification</h2>
                <p>Dear <strong>{user_access.name or user_access.email or 'Team'}</strong>,</p>
                <p>Your one-time verification code (OTP) for login is:</p>
                <div style="background-color: #f0f4f8; padding: 16px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #003b70; border-radius: 6px; margin: 20px 0;">
                    {otp_code}
                </div>
                <p style="color: #666; font-size: 14px;">This code will expire in 10 minutes. If you did not attempt to log in, please ignore this email.</p>
                <p style="font-size: 0.85em; color: #666; margin-top: 20px;">Regards,<br><b>Team HR</b></p>
            </div>
            """
            await AuthService.send_auth_email(user_access.email, "NDC Tracking - Login OTP Code", body_html)

            return {
                "requires_otp": True,
                "email": user_access.email,
                "message": "OTP verification code sent to your email."
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error in authenticate_user: {e}', exc_info=True)
            raise HTTPException(status_code=500, detail='An internal server error occurred.')

    @staticmethod
    async def verify_otp(email: str, otp_code: str, db: AsyncSession) -> dict:
        """Verify the OTP code sent to user email and issue session token."""
        try:
            email = email.strip().lower()
            otp_code = otp_code.strip()

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or request.")

            if user_access.status == "pending":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your access request is pending approval.")
            if user_access.status == "rejected":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Your request has been rejected.")

            if not user_access.otp_code or not user_access.otp_expires_at:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No OTP code requested or OTP has expired. Please log in again.")

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            otp_exp = user_access.otp_expires_at
            if otp_exp.tzinfo is not None:
                otp_exp = otp_exp.astimezone(timezone.utc).replace(tzinfo=None)

            if now > otp_exp:
                user_access.otp_code = None
                user_access.otp_expires_at = None
                await db.commit()
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired. Please request a new OTP.")

            if user_access.otp_code != otp_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code. Please check and try again.")

            # Clear OTP fields on successful verification
            user_access.otp_code = None
            user_access.otp_expires_at = None
            await db.commit()

            # Generate session token
            session_token = create_access_token({
                "sub": user_access.email,
                "role": user_access.role,
                "name": user_access.name or user_access.email.split('@')[0]
            })

            return {
                "token": session_token,
                "email": user_access.email,
                "role": user_access.role,
                "name": user_access.name or user_access.email.split('@')[0],
                "status": user_access.status
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error in verify_otp: {e}', exc_info=True)
            raise HTTPException(status_code=500, detail='An internal server error occurred.')

    @staticmethod
    async def resend_otp(email: str, db: AsyncSession) -> dict:
        """Resend OTP code to the specified email."""
        try:
            email = email.strip().lower()

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

            if user_access.status == "pending" or user_access.status == "rejected":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

            otp_code = f"{secrets.randbelow(900000) + 100000}"
            user_access.otp_code = otp_code
            user_access.otp_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)
            await db.commit()

            body_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h2 style="color: #003b70; margin-bottom: 16px;">NDC Tracking System - Login Verification</h2>
                <p>Dear <strong>{user_access.name or user_access.email or 'Team'}</strong>,</p>
                <p>Your new one-time verification code (OTP) for login is:</p>
                <div style="background-color: #f0f4f8; padding: 16px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #003b70; border-radius: 6px; margin: 20px 0;">
                    {otp_code}
                </div>
                <p style="color: #666; font-size: 14px;">This code will expire in 10 minutes. If you did not request this OTP, please ignore this email.</p>
                <p style="font-size: 0.85em; color: #666; margin-top: 20px;">Regards,<br><b>Team HR</b></p>
            </div>
            """
            await AuthService.send_auth_email(user_access.email, "NDC Tracking - New Login OTP Code", body_html)

            return {"message": "A new OTP has been sent to your email."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error in resend_otp: {e}', exc_info=True)
            raise HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def initiate_forgot_password(email: str, origin: str, db: AsyncSession) -> dict:
        """Generate a password reset token and send the reset email."""
        try:
            email = email.strip().lower()
            # if not email.endswith("@adani.com"):
            #     raise HTTPException(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         detail="Only @adani.com email addresses are allowed."
            #     )

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            generic_msg = "If an account exists with this email address, password reset instructions have been sent."

            if not user_access:
                return {"message": generic_msg}

            if user_access.status != "approved":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not approved for access.")

            # Generate token valid for 30 minutes
            reset_token = secrets.token_urlsafe(32)
            user_access.reset_token = reset_token
            user_access.reset_token_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
            db.add(user_access)
            await db.commit()

            # Build reset link
            reset_url = f"{origin}/ndc/reset-password?token={reset_token}"

            try:
                from app.modules.email.service import EmailService
                await EmailService.send_password_reset_email(email, reset_url)
            except Exception as e:
                logger.error("Failed to trigger password reset email: %s", str(e))

            return {"message": generic_msg}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in initiate_forgot_password: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def verify_reset_token_service(token: str, db: AsyncSession) -> dict:
        """Verify that a password reset token is valid and not expired."""
        try:
            stmt = select(NdcUserAccess).where(NdcUserAccess.reset_token == token)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=400, detail="Invalid or expired password reset link.")

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not user_access.reset_token_expires_at or user_access.reset_token_expires_at < now:
                raise HTTPException(status_code=400, detail="This password reset link has expired. Please request a new one.")

            return {"valid": True, "email": user_access.email}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in verify_reset_token_service: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def reset_password_service(token: str, new_password: str, db: AsyncSession) -> dict:
        """Reset a user's password using a valid reset token."""
        try:
            stmt = select(NdcUserAccess).where(NdcUserAccess.reset_token == token)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=400, detail="Invalid or expired password reset link.")

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not user_access.reset_token_expires_at or user_access.reset_token_expires_at < now:
                raise HTTPException(status_code=400, detail="This password reset link has expired. Please request a new one.")

            if not new_password or len(new_password.strip()) < 4:
                raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

            user_access.hashed_password = hash_password(new_password.strip())
            user_access.reset_token = None
            user_access.reset_token_expires_at = None

            db.add(user_access)
            await db.commit()

            return {"message": "Password reset successfully. You can now log in with your new password."}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in reset_password_service: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def get_auth_config() -> dict:
        """Return authentication configuration."""
        try:
            sso_enabled = os.getenv("SSO_ENABLED", "False").lower() in ("true", "1", "yes", "on")
            return {"sso_enabled": sso_enabled}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in get_auth_config: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def build_sso_login_url() -> tuple[bool, str | dict]:
        """Build Azure AD SSO login URL. Returns (sso_enabled, url_or_message)."""
        try:
            sso_enabled = os.getenv("SSO_ENABLED", "False").lower() in ("true", "1", "yes", "on")
            if not sso_enabled:
                return False, {"message": "SSO disabled, direct access"}

            client_id = os.getenv("AZURE_AD_CLIENT_ID")
            tenant_id = os.getenv("AZURE_AD_TENANT_ID")
            redirect_uri = os.getenv("AZURE_AD_REDIRECT_URI")

            if not all([client_id, tenant_id, redirect_uri]):
                raise HTTPException(status_code=500, detail="Azure AD environment configurations are incomplete.")

            state = secrets.token_urlsafe(32)

            auth_url = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?"
                f"client_id={client_id}&response_type=code&redirect_uri={redirect_uri}"
                f"&response_mode=query&scope=openid%20profile%20email%20User.Read&state={state}"
            )

            return True, {"url": auth_url, "state": state}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in build_sso_login_url: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def handle_sso_callback(
        code: str,
        state: str,
        cookie_state: str | None,
        base_url: str,
        ip_address: str | None,
        db: AsyncSession,
    ) -> dict:
        """Handle the Azure AD SSO callback: token exchange, user provisioning, audit logging.
        
        Returns a dict with 'action' key indicating what the router should do:
        - {"action": "redirect", "url": "..."} for redirects
        """
        try:
            if not code or not state:
                raise HTTPException(status_code=400, detail="Authorization code or state parameter is missing.")

            if not cookie_state or cookie_state != state:
                raise HTTPException(status_code=400, detail="State parameter mismatch. Possible CSRF attack.")

            client_id = os.getenv("AZURE_AD_CLIENT_ID")
            client_secret = os.getenv("AZURE_AD_CLIENT_SECRET")
            tenant_id = os.getenv("AZURE_AD_TENANT_ID")
            redirect_uri = os.getenv("AZURE_AD_REDIRECT_URI")

            # Exchange authorization code for token
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }

            async with httpx.AsyncClient() as client:
                token_res = await client.post(token_url, data=data)
                if token_res.status_code != 200:
                    logger.error(f"Failed token exchange: {token_res.text}")
                    raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_res.text}")
                tokens = token_res.json()

            id_token = tokens.get("id_token")
            if not id_token:
                raise HTTPException(status_code=400, detail="ID Token not returned by Azure AD.")

            # Verify ID Token
            payload = await AuthService.verify_azure_token(id_token, tenant_id, client_id)

            email = (payload.get("email") or payload.get("preferred_username") or payload.get("upn", "")).strip().lower()
            name = payload.get("name", email.split('@')[0])

            if not email:
                raise HTTPException(status_code=400, detail="No email address found in Azure AD token claims.")

            # Check Super Admin
            super_admins = AuthService._get_super_admins()

            # CASE A: Email is Super Admin
            if email in super_admins:
                # Seed/update in DB to ensure it exists
                stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
                res = await db.execute(stmt)
                user_access = res.scalar_one_or_none()

                if not user_access:
                    user_access = NdcUserAccess(
                        email=email,
                        name=name,
                        role="super_admin",
                        status="approved",
                        approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        approved_by="system"
                    )
                    db.add(user_access)
                else:
                    user_access.role = "super_admin"
                    user_access.status = "approved"
            
                await db.commit()

                # Log audit
                audit_log = NdcAuthAuditLog(
                    event_type="LOGIN_SUCCESS",
                    email=email,
                    role="super_admin",
                    performed_by=email,
                    ip_address=ip_address,
                    notes="Super admin logged in"
                )
                db.add(audit_log)
                await db.commit()

                # Create session token
                session_token = create_access_token({"sub": email, "role": "super_admin", "name": name})
                return {
                    "action": "redirect",
                    "url": f"/ndc/ndc-reporting/overview?token={session_token}&email={email}&role=super_admin&name={name}"
                }

            # Database lookup for other users
            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            # CASE E: First-time login
            if not user_access:
                approval_token = secrets.token_urlsafe(32)
                user_access = NdcUserAccess(
                    email=email,
                    name=name,
                    role="admin",
                    status="pending",
                    approval_token=approval_token
                )
                db.add(user_access)
                await db.commit()

                # Send approval request email to super admins
                approve_link = f"{base_url}/api/auth/approve-access?token={approval_token}"
                reject_link = f"{base_url}/api/auth/reject-access?token={approval_token}"

                email_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                        <h2 style="color: #0b3d91; border-bottom: 2px solid #0b3d91; padding-bottom: 10px;">NDC System — New Access Request</h2>
                        <p>Dear Team,</p>
                        <p>A new user has logged in via SSO for the first time and is requesting administrative access to the <b>NDC &amp; F&amp;F Tracking System</b>.</p>
                    
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; width: 30%;">User Name:</td>
                                <td style="padding: 8px;">{name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">User Email:</td>
                                <td style="padding: 8px;">{email}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold;">Requested Role:</td>
                                <td style="padding: 8px;">admin</td>
                            </tr>
                        </table>

                        <p>Please review and act on this request immediately by clicking one of the buttons below:</p>
                        <div style="margin: 30px 0; text-align: center;">
                            <a href="{approve_link}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; margin-right: 15px;">APPROVE ACCESS</a>
                            <a href="{reject_link}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">REJECT ACCESS</a>
                        </div>
                        <p style="font-size: 0.9em; color: #777;">This email link is single-use and will be invalidated once clicked.</p>
                        <hr style="border: 0; border-top: 1px solid #eee;" />
                        <p style="font-size: 0.85em; color: #999;">Regards,<br><b>Team HR</b></p>
                    </div>
                </body>
                </html>
                """

                for sa_email in super_admins:
                    await AuthService.send_auth_email(to_email=sa_email, subject="NDC System — New Access Request", body_html=email_body)

                # Log audit
                audit_log = NdcAuthAuditLog(
                    event_type="FIRST_LOGIN_REQUEST_SENT",
                    email=email,
                    role="admin",
                    performed_by="system",
                    ip_address=ip_address,
                    notes="First-time login, access request sent"
                )
                db.add(audit_log)
                await db.commit()

                return {"action": "redirect", "url": f"/ndc/pending?email={email}"}

            # CASE B: Approved User
            if user_access.status == "approved":
                audit_log = NdcAuthAuditLog(
                    event_type="LOGIN_SUCCESS",
                    email=email,
                    role=user_access.role,
                    performed_by=email,
                    ip_address=ip_address,
                    notes="Admin logged in successfully"
                )
                db.add(audit_log)
                await db.commit()

                session_token = create_access_token({"sub": email, "role": user_access.role, "name": name})
                return {
                    "action": "redirect",
                    "url": f"/ndc/ndc-reporting/overview?token={session_token}&email={email}&role={user_access.role}&name={name}"
                }

            # CASE C: Pending User
            if user_access.status == "pending":
                audit_log = NdcAuthAuditLog(
                    event_type="LOGIN_BLOCKED_PENDING",
                    email=email,
                    role=user_access.role,
                    performed_by=email,
                    ip_address=ip_address,
                    notes="Login blocked: approval pending"
                )
                db.add(audit_log)
                await db.commit()

                return {"action": "redirect", "url": f"/ndc/pending?email={email}"}

            # CASE D: Rejected User
            if user_access.status == "rejected":
                audit_log = NdcAuthAuditLog(
                    event_type="LOGIN_BLOCKED_REJECTED",
                    email=email,
                    role=user_access.role,
                    performed_by=email,
                    ip_address=ip_address,
                    notes="Login blocked: user access rejected"
                )
                db.add(audit_log)
                await db.commit()

                return {"action": "redirect", "url": f"/ndc/access-denied?email={email}"}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in handle_sso_callback: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def approve_user_access(token: str, db: AsyncSession) -> dict:
        """Approve a user's access request via approval token.
        
        Returns a dict with 'found' flag and 'html' content for the response.
        """
        try:
            stmt = select(NdcUserAccess).where(NdcUserAccess.approval_token == token)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                return {
                    "found": False,
                    "html": """
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 100px; background-color: #f8f9fa;">
                    <div style="max-width: 500px; margin: auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <div style="font-size: 48px; color: #dc3545; margin-bottom: 20px;">⚠️</div>
                        <h2 style="color: #343a40;">Link Invalid or Expired</h2>
                        <p style="color: #6c757d; font-size: 1.1em;">This access approval link has already been used or is invalid.</p>
                    </div>
                </body>
                </html>
                """
                }

            email = user_access.email
            name = user_access.name or email.split('@')[0]

            # Update status to approved and clear approval_token
            user_access.status = "approved"
            user_access.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
            user_access.approved_by = "super_admin"
            user_access.approval_token = None

            db.add(user_access)

            # Log audit
            audit_log = NdcAuthAuditLog(
                event_type="ACCESS_APPROVED",
                email=email,
                role=user_access.role,
                performed_by="super_admin",
                notes="Access approved via email link"
            )
            db.add(audit_log)
            await db.commit()

            # Send confirmation email to user
            user_email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 10px;">NDC System — Access Granted</h2>
                    <p>Dear {name or 'Team'},</p>
                    <p>Your access request to the <b>NDC &amp; F&amp;F Tracking and Reporting System</b> has been approved by the administrator.</p>
                    <p>You can now log in to the portal using your Adani corporate account.</p>
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="/ndc" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">GO TO NDC TRACKING SYSTEM</a>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #eee;" />
                    <p style="font-size: 0.85em; color: #999;">Regards,<br><b>Team HR</b></p>
                </div>
            </body>
            </html>
            """
            await AuthService.send_auth_email(to_email=email, subject="NDC System — Access Granted", body_html=user_email_body)

            return {
                "found": True,
                "html": """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 100px; background-color: #f8f9fa;">
                <div style="max-width: 500px; margin: auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <div style="font-size: 48px; color: #28a745; margin-bottom: 20px;">✓</div>
                    <h2 style="color: #343a40; margin-bottom: 10px;">Access Approved</h2>
                    <p style="color: #6c757d; font-size: 1.1em;">You have successfully approved access for <strong>{}</strong>.</p>
                    <p style="color: #6c757d; font-size: 1.1em;">An email confirmation has been dispatched to the user.</p>
                </div>
            </body>
            </html>
            """.format(email)
            }
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in approve_user_access: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def reject_user_access(token: str, db: AsyncSession) -> dict:
        """Reject a user's access request via approval token.
        
        Returns a dict with 'found' flag and 'html' content for the response.
        """
        try:
            stmt = select(NdcUserAccess).where(NdcUserAccess.approval_token == token)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                return {
                    "found": False,
                    "html": """
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 100px; background-color: #f8f9fa;">
                    <div style="max-width: 500px; margin: auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                        <div style="font-size: 48px; color: #dc3545; margin-bottom: 20px;">⚠️</div>
                        <h2 style="color: #343a40;">Link Invalid or Expired</h2>
                        <p style="color: #6c757d; font-size: 1.1em;">This access rejection link has already been used or is invalid.</p>
                    </div>
                </body>
                </html>
                """
                }

            email = user_access.email
            name = user_access.name or email.split('@')[0]

            # Update status to rejected and clear approval_token
            user_access.status = "rejected"
            user_access.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            user_access.reviewed_by = "super_admin"
            user_access.approval_token = None

            db.add(user_access)

            # Log audit
            audit_log = NdcAuthAuditLog(
                event_type="ACCESS_REJECTED",
                email=email,
                role=user_access.role,
                performed_by="super_admin",
                notes="Access rejected via email link"
            )
            db.add(audit_log)
            await db.commit()

            # Send rejection email to user
            user_email_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #dc3545; border-bottom: 2px solid #dc3545; padding-bottom: 10px;">NDC System — Access Denied</h2>
                    <p>Dear {name or 'Team'},</p>
                    <p>Your access request to the <b>NDC &amp; F&amp;F Tracking and Reporting System</b> has been declined.</p>
                    <p>If you believe this is a mistake, please contact the system administrator for assistance.</p>
                    <hr style="border: 0; border-top: 1px solid #eee;" />
                    <p style="font-size: 0.85em; color: #999;">Regards,<br><b>Team HR</b></p>
                </div>
            </body>
            </html>
            """
            await AuthService.send_auth_email(to_email=email, subject="NDC System — Access Denied", body_html=user_email_body)

            return {
                "found": True,
                "html": """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding-top: 100px; background-color: #f8f9fa;">
                <div style="max-width: 500px; margin: auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                    <div style="font-size: 48px; color: #dc3545; margin-bottom: 20px;">✕</div>
                    <h2 style="color: #343a40; margin-bottom: 10px;">Access Denied</h2>
                    <p style="color: #6c757d; font-size: 1.1em;">You have rejected access for <strong>{}</strong>.</p>
                    <p style="color: #6c757d; font-size: 1.1em;">The user has been notified of the decision.</p>
                </div>
            </body>
            </html>
            """.format(email)
            }
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in reject_user_access: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def logout_user(auth_header: str | None, ip_address: str | None, db: AsyncSession) -> dict:
        """Log out a user and return logout URL."""
        try:
            email = "unknown"
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    email = decode_jwt_token(token) or "unknown"
                except Exception:
                    pass

            # Log audit
            audit_log = NdcAuthAuditLog(
                event_type="SESSION_REVOKED",
                email=email,
                performed_by=email,
                ip_address=ip_address,
                notes="User logged out successfully"
            )
            db.add(audit_log)
            await db.commit()

            # In a full Azure flow we can also return a logout redirect URL
            tenant_id = os.getenv("AZURE_AD_TENANT_ID")
            logout_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout?post_logout_redirect_uri="
            return {"message": "Logged out successfully", "logout_url": logout_url}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in logout_user: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def get_current_user_info(email: str, current_user: dict, db: AsyncSession) -> dict:
        """Get information about the currently authenticated user."""
        try:
            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                # Check if they are configured as Super Admin
                super_admins = AuthService._get_super_admins()
                if email in super_admins:
                    return {
                        "email": email,
                        "name": current_user.get("name", email.split('@')[0]),
                        "role": "super_admin",
                        "status": "approved"
                    }
                raise HTTPException(status_code=403, detail="User access record not found in system.")

            return {
                "email": user_access.email,
                "name": user_access.name,
                "role": user_access.role,
                "status": user_access.status
            }
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in get_current_user_info: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


