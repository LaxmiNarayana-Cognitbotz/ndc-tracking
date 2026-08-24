from fastapi import HTTPException
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.auth.jwt_bearer import get_current_user
from app.dto.auth import UserCreateRequest, UserUpdateRequest
from app.modules.users.service import UsersService
from config.database import get_db

logger = logging.getLogger(__name__)
# SUPER ADMIN ADMIN ACTIONS (under /api/admin)
# ==============================================================================

# Custom dependency to enforce super_admin access
async def require_super_admin(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        email = current_user.get("sub")
        return await UsersService.verify_super_admin(email, db)
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.error(f'Error in require_super_admin: {e}', exc_info=True)
        import fastapi
        raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


admin_router = APIRouter(prefix="/api/admin", tags=["Admin Management"], dependencies=[Depends(require_super_admin)])


@admin_router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.list_all_users(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.put("/users/{email}/revoke")
async def revoke_access(email: str, db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.revoke_user_access_by_email(email, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.post("/users")
async def create_user(payload: UserCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.create_user_service(payload.email, payload.name, payload.role, payload.password, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.put("/users/{email}")
async def update_user(email: str, payload: UserUpdateRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.update_user_service(email, payload.name, payload.role, payload.status, payload.password, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.delete("/users/{email}")
async def delete_user(email: str, db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.delete_user_service(email, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.delete("/ndc-records/{person_number}")
async def delete_ndc_record_endpoint(
    person_number: int,
    reason: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        deleted_by = current_user.get("sub") or "super_admin"
        return await UsersService.delete_ndc_record(person_number, deleted_by, reason, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@admin_router.get("/audit-logs")
async def list_audit_logs(page: int = 1, limit: int = 50, db: AsyncSession = Depends(get_db)):
    try:
        return await UsersService.list_audit_logs_service(page, limit, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
