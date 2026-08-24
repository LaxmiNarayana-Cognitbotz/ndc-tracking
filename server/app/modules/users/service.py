import logging
import os
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ndc_approval import NdcApproval
from app.models.ndc_auth_audit_log import NdcAuthAuditLog
from app.models.ndc_deleted_record import NdcDeletedRecord
from app.models.ndc_record import NdcRecord
from app.models.ndc_user_access import NdcUserAccess
from app.utils.password import hash_password

logger = logging.getLogger(__name__)


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


class UsersService:
    @staticmethod
    async def verify_super_admin(email: str, db: AsyncSession) -> str:
        """Verify that a user has super_admin role. Returns the role string."""
        try:
            if not email:
                raise HTTPException(status_code=401, detail="Unauthorized")

            # Check hardcoded list first
            super_admins = _get_super_admins()
            if email in super_admins:
                return "super_admin"

            stmt = select(NdcUserAccess.role).where(NdcUserAccess.email == email, NdcUserAccess.status == "approved")
            res = await db.execute(stmt)
            role = res.scalar_one_or_none()

            if role != "super_admin":
                raise HTTPException(status_code=403, detail="Access denied. Super Admin role required.")
            
            return role
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in verify_super_admin: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    # ── Admin Management Service Functions ────────────────────────────────────────

    @staticmethod
    async def list_all_users(db: AsyncSession) -> list[dict]:
        """List all users ordered by requested_at descending."""
        try:
            stmt = select(NdcUserAccess).order_by(NdcUserAccess.requested_at.desc())
            res = await db.execute(stmt)
            users = res.scalars().all()
            return [
                {
                    "id": u.id,
                    "email": u.email,
                    "name": u.name,
                    "role": u.role,
                    "status": u.status,
                    "requested_at": u.requested_at.isoformat() if u.requested_at else None,
                    "approved_at": u.approved_at.isoformat() if u.approved_at else None,
                    "approved_by": u.approved_by,
                    "reviewed_at": u.reviewed_at.isoformat() if u.reviewed_at else None,
                    "reviewed_by": u.reviewed_by,
                    "notes": u.notes
                }
                for u in users
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in list_all_users: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def revoke_user_access_by_email(email: str, db: AsyncSession) -> dict:
        """Revoke a user's access by email."""
        try:
            email_clean = email.strip().lower()
            
            # Check if they are trying to revoke a super_admin from env list
            super_admins = _get_super_admins()
            if email_clean in super_admins:
                raise HTTPException(status_code=400, detail="Cannot revoke root super admins configured via environment variables.")

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email_clean)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=404, detail="User access record not found.")

            user_access.status = "rejected"
            user_access.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            user_access.reviewed_by = "super_admin"
            user_access.approval_token = None
            db.add(user_access)

            # Log audit
            audit_log = NdcAuthAuditLog(
                event_type="SESSION_REVOKED",
                email=email_clean,
                role=user_access.role,
                performed_by="super_admin",
                notes="User access revoked by super admin"
            )
            db.add(audit_log)
            await db.commit()

            return {"message": f"Access successfully revoked for {email_clean}."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in revoke_user_access_by_email: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def create_user_service(
        email: str,
        name: str,
        role: str,
        password: str,
        db: AsyncSession,
    ) -> dict:
        """Create a new user."""
        try:
            email = email.strip().lower()
            # if not email.endswith("@adani.com"):
            #     raise HTTPException(status_code=400, detail="Only @adani.com email addresses are allowed.")

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email)
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=400, detail="User with this email already exists.")

            new_user = NdcUserAccess(
                email=email,
                name=name,
                role=role,
                status="approved",
                hashed_password=hash_password(password),
                approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                approved_by="super_admin"
            )
            db.add(new_user)
            await db.commit()
            return {"message": "User created successfully", "email": email}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in create_user_service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def update_user_service(
        email: str,
        name: str | None,
        role: str | None,
        user_status: str | None,
        password: str | None,
        db: AsyncSession,
    ) -> dict:
        """Update an existing user."""
        try:
            email_clean = email.strip().lower()
            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email_clean)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=404, detail="User not found.")

            super_admins = _get_super_admins()

            if email_clean in super_admins:
                if role and role != "super_admin":
                    raise HTTPException(status_code=400, detail="Cannot downgrade root super admins configured via environment variables.")
                if user_status and user_status != "approved":
                    raise HTTPException(status_code=400, detail="Cannot change status of root super admins configured via environment variables.")

            if name is not None:
                user_access.name = name
            if role is not None:
                user_access.role = role
            if user_status is not None:
                user_access.status = user_status
            if password is not None and password.strip() != "":
                user_access.hashed_password = hash_password(password)

            db.add(user_access)
            await db.commit()
            return {"message": "User updated successfully", "email": email_clean}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in update_user_service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def delete_user_service(email: str, db: AsyncSession) -> dict:
        """Delete a user by email."""
        try:
            email_clean = email.strip().lower()
            super_admins = _get_super_admins()

            if email_clean in super_admins:
                raise HTTPException(status_code=400, detail="Cannot delete root super admins configured via environment variables.")

            stmt = select(NdcUserAccess).where(NdcUserAccess.email == email_clean)
            res = await db.execute(stmt)
            user_access = res.scalar_one_or_none()

            if not user_access:
                raise HTTPException(status_code=404, detail="User not found.")

            await db.delete(user_access)
            await db.commit()
            return {"message": "User deleted successfully", "email": email_clean}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in delete_user_service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def list_audit_logs_service(page: int, limit: int, db: AsyncSession) -> dict:
        """List audit logs with pagination."""
        try:
            offset = (page - 1) * limit
            stmt = select(NdcAuthAuditLog).order_by(NdcAuthAuditLog.created_at.desc()).offset(offset).limit(limit)
            res = await db.execute(stmt)
            logs = res.scalars().all()
            
            # Fetch total count
            count_stmt = select(func.count(NdcAuthAuditLog.id))
            count_res = await db.execute(count_stmt)
            total = count_res.scalar() or 0

            return {
                "logs": [
                    {
                        "id": l.id,
                        "event_type": l.event_type,
                        "email": l.email,
                        "role": l.role,
                        "performed_by": l.performed_by,
                        "ip_address": l.ip_address,
                        "created_at": l.created_at.isoformat() if l.created_at else None,
                        "notes": l.notes
                    }
                    for l in logs
                ],
                "total": total,
                "page": page,
                "limit": limit
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in list_audit_logs_service: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")


    @staticmethod
    async def delete_ndc_record(person_number: int, deleted_by: str, reason: str | None, db: AsyncSession) -> dict:
        """Delete an NDC employee record and persistently add them to the exclusion list."""
        try:
            # 1. Fetch the employee record
            stmt = select(NdcRecord).where(NdcRecord.person_number == person_number)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()

            if not record:
                raise HTTPException(status_code=404, detail=f"Employee with person number {person_number} not found.")

            employee_name = record.employee_name

            # 2. Check if already in ndc_deleted_records
            del_stmt = select(NdcDeletedRecord).where(NdcDeletedRecord.person_number == person_number)
            del_res = await db.execute(del_stmt)
            existing_deleted = del_res.scalar_one_or_none()

            if not existing_deleted:
                deleted_entry = NdcDeletedRecord(
                    person_number=person_number,
                    employee_name=employee_name,
                    deleted_by=deleted_by,
                    reason=reason.strip() if reason else None
                )
                db.add(deleted_entry)
            else:
                existing_deleted.deleted_by = deleted_by
                existing_deleted.reason = reason.strip() if reason else None

            # 3. Delete approvals and ndc_record
            await db.execute(delete(NdcApproval).where(NdcApproval.ndc_record_id == record.id))
            await db.delete(record)

            # 4. Record in audit log
            audit_log = NdcAuthAuditLog(
                event_type="employee_deletion",
                email=deleted_by,
                role="super_admin",
                performed_by=deleted_by,
                notes=f"Permanently deleted employee {employee_name} (Person Number: {person_number}). Reason: {reason or 'None'}"
            )
            db.add(audit_log)

            await db.commit()
            return {
                "message": f"Employee {employee_name} ({person_number}) permanently deleted and excluded from future syncs.",
                "person_number": person_number
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in delete_ndc_record: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
