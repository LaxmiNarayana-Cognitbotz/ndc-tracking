import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ndc_user_access import NdcUserAccess
from app.utils.password import hash_password

logger = logging.getLogger(__name__)



class StartupService:
    @staticmethod
    async def run_migrations(session: AsyncSession) -> None:
        """Run idempotent schema migrations to add any columns missing from older DB instances.

        Each column is migrated in isolation (its own try/except + commit/rollback) so that
        a failure on one column does NOT abort the others or leave the session in a broken state.
        This is the primary defence against UndefinedColumnError crashes on the Azure VM.
        """

        async def _add_column(ddl: str) -> None:
            """Execute a single ADD COLUMN IF NOT EXISTS statement, swallowing errors gracefully."""
            try:
                await session.execute(text(ddl))
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.warning("Migration skipped (column may already exist): %s", exc)

        # ── ndc_user_access columns ──────────────────────────────────────────────
        await _add_column("ALTER TABLE ndc_user_access ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)")
        await _add_column("ALTER TABLE ndc_user_access ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)")
        await _add_column("ALTER TABLE ndc_user_access ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP")
        await _add_column("ALTER TABLE ndc_user_access ADD COLUMN IF NOT EXISTS otp_code VARCHAR(10)")
        await _add_column("ALTER TABLE ndc_user_access ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP")

        # ── ndc_records: F&F tracking columns ───────────────────────────────────
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS is_fnf_completed BOOLEAN NOT NULL DEFAULT false")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS is_fnf_closed BOOLEAN NOT NULL DEFAULT false")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS is_fnf_revision BOOLEAN NOT NULL DEFAULT false")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS is_fnf_email_sent BOOLEAN NOT NULL DEFAULT false")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS is_fnf_revision_email_sent BOOLEAN NOT NULL DEFAULT false")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS fnf_completed_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS gcc_initiate_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS fnf_document_count INTEGER NOT NULL DEFAULT 0")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS fnf_revision_start_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS fnf_revision_completed_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS fnf_revision_comment VARCHAR(1000)")

        # ── ndc_records: department approval date columns ────────────────────────
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS rm_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS it_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS abex_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS telecom_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS store_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS safety_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS administration_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS security_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS hr_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS gcc_hr_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS final_abex_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS business_specific_approval_date DATE")
        await _add_column("ALTER TABLE ndc_records ADD COLUMN IF NOT EXISTS legatrix_approval_date DATE")

        # ── ndc_deleted_records: persistent exclusion table ──────────────────────
        await _add_column("""
            CREATE TABLE IF NOT EXISTS ndc_deleted_records (
                id SERIAL PRIMARY KEY,
                person_number BIGINT UNIQUE NOT NULL,
                employee_name VARCHAR(200),
                deleted_by VARCHAR(200) NOT NULL,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason VARCHAR(500)
            )
        """)
        await _add_column("CREATE INDEX IF NOT EXISTS idx_deleted_person_number ON ndc_deleted_records(person_number)")

        logger.info("Schema migrations completed.")


    @staticmethod
    async def seed_super_admins(session: AsyncSession) -> None:
        try:
            """Seed or ensure super admin users exist in the database."""
            super_admin_env = os.getenv("SUPER_ADMIN_EMAIL", "")
            super_admins = [e.strip().lower() for e in super_admin_env.split(",") if e.strip()]

            for sa_email in super_admins:
                stmt = select(NdcUserAccess).where(NdcUserAccess.email == sa_email)
                res = await session.execute(stmt)
                user_access = res.scalar_one_or_none()
                if not user_access:
                    logger.info(f"Seeding super admin: {sa_email}")
                    user_access = NdcUserAccess(
                        email=sa_email,
                        name=sa_email.split('@')[0],
                        role="super_admin",
                        status="approved",
                        hashed_password=hash_password("Adani@123"),
                        approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        approved_by="system"
                    )
                    session.add(user_access)
                else:
                    logger.info(f"Ensuring super admin privileges: {sa_email}")
                    user_access.role = "super_admin"
                    user_access.status = "approved"
                    if not user_access.hashed_password:
                        user_access.hashed_password = hash_password("Adani@123")
                    # Update attributes in-place to ensure SQLAlchemy flushes correctly
                    session.add(user_access)


        except Exception as e:
            import logging; logging.error('Error in seed_super_admins: %s', e, exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail='An internal error occurred.')

    @staticmethod
    async def seed_demo_admin(session: AsyncSession) -> None:
        try:
            """Seed the demo admin user if it doesn't exist."""
            stmt = select(NdcUserAccess).where(NdcUserAccess.email == "demo.admin@adani.com")
            res = await session.execute(stmt)
            demo_admin = res.scalar_one_or_none()
            if not demo_admin:
                logger.info("Seeding demo admin: demo.admin@adani.com")
                demo_admin = NdcUserAccess(
                    email="demo.admin@adani.com",
                    name="Demo Admin",
                    role="admin",
                    status="approved",
                    hashed_password=hash_password("Adani@123"),
                    approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    approved_by="system"
                )
                session.add(demo_admin)
            else:
                if not demo_admin.hashed_password:
                    demo_admin.hashed_password = hash_password("Adani@123")
                session.add(demo_admin)
        except Exception as e:
            import logging; logging.error('Error in seed_demo_admin: %s', e, exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail='An internal error occurred.')
