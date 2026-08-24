import io
import logging
import re
from typing import Any, Dict, List, Tuple

import pandas as pd
from fastapi import UploadFile, status
from fastapi.exceptions import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.rm_email_configuration import RmEmailCreate, RmEmailUpdate
from app.models.rm_email_configuration import RmEmailConfiguration

logger = logging.getLogger(__name__)



class RMEmailService:
    @staticmethod
    async def create_rm_email(config: RmEmailCreate, db: AsyncSession) -> RmEmailConfiguration:
        """Create a new RM email configuration record."""
        try:
            email_str = config.email.strip().lower()

            email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(email_regex, email_str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")

            # Duplicate check
            res = await db.execute(select(RmEmailConfiguration).where(RmEmailConfiguration.email == email_str))
            existing = res.scalar_one_or_none()

            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RM with this email already exists")

            new_config = RmEmailConfiguration(
                rm_name=config.rm_name.strip(),
                email=email_str
            )
            db.add(new_config)
            await db.commit()
            return new_config
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to create RM email configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )


    @staticmethod
    async def get_rm_emails_paginated(
        page: int, limit: int, search: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """Retrieve paginated and filtered RM email configurations."""
        try:
            if page < 1:
                page = 1
            if limit < 1:
                limit = 10

            # Build select query
            query = select(RmEmailConfiguration)
            if search:
                search_pattern = f"%{search.strip()}%"
                query = query.where(
                    (RmEmailConfiguration.rm_name.ilike(search_pattern)) |
                    (RmEmailConfiguration.email.ilike(search_pattern))
                )

            # Order by RM Name ascending
            query = query.order_by(RmEmailConfiguration.rm_name.asc())

            # Count total matching records
            count_q = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_q)
            total = total_result.scalar() or 0

            # Offset & Limit pagination
            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)

            # Execute query
            res = await db.execute(query)
            records = res.scalars().all()

            # Map records to list of dicts
            data = [
                {
                    "id": r.id,
                    "rm_name": r.rm_name,
                    "email": r.email,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
                    "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else None
                }
                for r in records
            ]

            total_pages = (total + limit - 1) // limit if total > 0 else 0

            return {
                "data": data,
                "page": page,
                "limit": limit,
                "total": total,
                "totalPages": total_pages
            }
        except Exception as e:
            logger.exception("Failed to retrieve RM email configurations")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve configurations: {str(e)}"
            )


    @staticmethod
    async def import_rm_emails_excel(file: UploadFile, db: AsyncSession) -> Dict[str, Any]:
        """Import RM configurations from an uploaded Excel file."""
        try:
            if not file.filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

            ext = file.filename.split(".")[-1].lower()
            if ext not in ("xlsx", "xls"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: .{ext}. Only .xlsx and .xls are allowed."
                )

            try:
                content = await file.read()
                df = pd.read_excel(io.BytesIO(content))
            except Exception as e:
                logger.exception("Failed to parse imported Excel file")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to parse Excel file: {str(e)}"
                )

            # Clean and check columns
            df.columns = [str(col).strip() for col in df.columns]

            col_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == "rm name":
                    col_mapping["rm_name"] = col
                elif col_lower == "email":
                    col_mapping["email"] = col

            if "rm_name" not in col_mapping or "email" not in col_mapping:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excel file must contain 'RM Name' and 'Email' columns."
                )

            inserted = 0
            skipped = 0
            failed = 0
            errors = []

            try:
                # Get all existing emails for duplicate checking
                res = await db.execute(select(RmEmailConfiguration.email))
                existing_emails = {e.lower() for e in res.scalars().all()}
            
                seen_emails = set()

                for idx, row in df.iterrows():
                    row_num = idx + 2  # Row index starts at 2 (Row 1 is header)
                
                    raw_rm_name = row[col_mapping["rm_name"]]
                    raw_email = row[col_mapping["email"]]

                    # Skip completely empty rows
                    if pd.isna(raw_rm_name) and pd.isna(raw_email):
                        continue

                    rm_name_str = str(raw_rm_name).strip() if not pd.isna(raw_rm_name) else ""
                    email_str = str(raw_email).strip().lower() if not pd.isna(raw_email) else ""

                    if not rm_name_str and not email_str:
                        continue

                    # Validations
                    if not rm_name_str:
                        errors.append({"row": row_num, "message": "RM Name is required"})
                        failed += 1
                        continue

                    if not email_str:
                        errors.append({"row": row_num, "message": "Email is required"})
                        failed += 1
                        continue

                    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
                    if not re.match(email_regex, email_str):
                        errors.append({"row": row_num, "message": "Invalid email format"})
                        failed += 1
                        continue

                    # Duplicate check
                    if email_str in existing_emails or email_str in seen_emails:
                        skipped += 1
                        continue

                    seen_emails.add(email_str)
                    new_config = RmEmailConfiguration(
                        rm_name=rm_name_str,
                        email=email_str
                    )
                    db.add(new_config)
                    inserted += 1

                if inserted > 0:
                    await db.commit()

                return {
                    "success": True,
                    "inserted": inserted,
                    "skipped": skipped,
                    "failed": failed,
                    "errors": errors
                }
            except Exception as e:
                logger.exception("Failed to import configuration data into database")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database import failed: {str(e)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in import_rm_emails_excel: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def generate_sample_excel() -> io.BytesIO:
        """Generate sample Excel bytes for RM Configuration import template."""
        try:
            data = [
                {"RM Name": "RM North", "Email": "rmnorth@company.com"},
                {"RM Name": "RM West", "Email": "rmwest@company.com"}
            ]
            df = pd.DataFrame(data)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Sample")
            output.seek(0)
            return output
        except Exception as e:
            logger.exception("Failed to generate sample Excel file")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate template: {str(e)}"
            )


    @staticmethod
    async def delete_rm_email(id: int, db: AsyncSession) -> bool:
        """Delete an RM configuration by ID. Returns True if deleted, False if not found."""
        try:
            res = await db.execute(select(RmEmailConfiguration).where(RmEmailConfiguration.id == id))
            config = res.scalar_one_or_none()
            
            if not config:
                return False
                
            await db.delete(config)
            await db.commit()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete RM configuration {id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete failed: {str(e)}"
            )


    @staticmethod
    async def update_rm_email(id: int, config: RmEmailUpdate, db: AsyncSession) -> RmEmailConfiguration:
        """Update an existing RM configuration."""
        try:
            email_str = config.email.strip().lower()
            
            email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(email_regex, email_str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
            
            res = await db.execute(select(RmEmailConfiguration).where(RmEmailConfiguration.id == id))
            existing = res.scalar_one_or_none()
            
            if not existing:
                return None
            
            # Duplicate check: check if another record with the same email already exists (excluding current record)
            res_dup = await db.execute(
                select(RmEmailConfiguration)
                .where(RmEmailConfiguration.email == email_str)
                .where(RmEmailConfiguration.id != id)
            )
            duplicate = res_dup.scalar_one_or_none()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RM with this email already exists")
            
            existing.rm_name = config.rm_name.strip()
            existing.email = email_str
            
            await db.commit()
            return existing
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to update RM configuration {id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Update failed: {str(e)}"
            )
