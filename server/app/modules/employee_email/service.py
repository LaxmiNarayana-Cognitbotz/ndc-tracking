import io
import logging
import re
from typing import Any, Dict, List, Tuple

import pandas as pd
from fastapi import UploadFile, status
from fastapi.exceptions import HTTPException
from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.employee_email_master import EmployeeEmailCreate, EmployeeEmailUpdate
from app.models.employee_email_master import EmployeeEmailMaster

logger = logging.getLogger(__name__)



class EmployeeEmailService:
    @staticmethod
    async def create_employee_email(config: EmployeeEmailCreate, db: AsyncSession) -> EmployeeEmailMaster:
        """Create a new Employee email configuration record."""
        try:
            email_str = config.email.strip().lower()

            email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(email_regex, email_str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")

            # Duplicate check on person_number
            res = await db.execute(select(EmployeeEmailMaster).where(EmployeeEmailMaster.person_number == config.person_number))
            existing = res.scalar_one_or_none()

            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee with this Person Number already exists")

            new_config = EmployeeEmailMaster(
                person_number=config.person_number,
                employee_name=config.employee_name.strip(),
                email=email_str
            )
            db.add(new_config)
            await db.commit()
            return new_config
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to create employee email configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )


    @staticmethod
    async def get_employee_emails_paginated(
        page: int, limit: int, search: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """Retrieve paginated and filtered Employee email configurations."""
        try:
            if page < 1:
                page = 1
            if limit < 1:
                limit = 10

            # Build select query
            query = select(EmployeeEmailMaster)
            if search:
                search_pattern = f"%{search.strip()}%"
                # Support search by employee name, email, or string version of person number
                query = query.where(
                    (EmployeeEmailMaster.employee_name.ilike(search_pattern)) |
                    (EmployeeEmailMaster.email.ilike(search_pattern)) |
                    (func.cast(EmployeeEmailMaster.person_number, String).ilike(search_pattern))
                )

            # Order by Employee Name ascending
            query = query.order_by(EmployeeEmailMaster.employee_name.asc())

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
                    "person_number": r.person_number,
                    "employee_name": r.employee_name,
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
            logger.exception("Failed to retrieve Employee email configurations")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve configurations: {str(e)}"
            )


    @staticmethod
    async def import_employee_emails_excel(file: UploadFile, db: AsyncSession) -> Dict[str, Any]:
        """Import Employee configurations from an uploaded Excel file."""
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
                if col_lower in ("person number", "person_number", "emp id", "employee id"):
                    col_mapping["person_number"] = col
                elif col_lower in ("employee name", "employee_name", "emp name", "name"):
                    col_mapping["employee_name"] = col
                elif col_lower == "email":
                    col_mapping["email"] = col

            if "person_number" not in col_mapping or "employee_name" not in col_mapping or "email" not in col_mapping:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excel file must contain 'Person Number', 'Employee Name' and 'Email' columns."
                )

            inserted = 0
            updated = 0
            failed = 0
            errors = []

            try:
                # Get all existing records keyed by person_number for upsert logic
                res = await db.execute(select(EmployeeEmailMaster))
                existing_records = {r.person_number: r for r in res.scalars().all()}
            
                seen_person_numbers = set()

                for idx, row in df.iterrows():
                    row_num = idx + 2  # Row index starts at 2 (Row 1 is header)
                
                    raw_person_num = row[col_mapping["person_number"]]
                    raw_employee_name = row[col_mapping["employee_name"]]
                    raw_email = row[col_mapping["email"]]

                    # Skip completely empty rows
                    if pd.isna(raw_person_num) and pd.isna(raw_employee_name) and pd.isna(raw_email):
                        continue

                    person_num_str = str(raw_person_num).strip() if not pd.isna(raw_person_num) else ""
                    employee_name_str = str(raw_employee_name).strip() if not pd.isna(raw_employee_name) else ""
                    email_str = str(raw_email).strip().lower() if not pd.isna(raw_email) else ""

                    if not person_num_str and not employee_name_str and not email_str:
                        continue

                    # Validations
                    if not person_num_str:
                        errors.append({"row": row_num, "message": "Person Number is required"})
                        failed += 1
                        continue

                    # Parse person number as int
                    try:
                        # Remove decimals if float got imported (e.g. 12345.0)
                        if "." in person_num_str:
                            person_num_val = int(float(person_num_str))
                        else:
                            person_num_val = int(person_num_str)
                    except ValueError:
                        errors.append({"row": row_num, "message": f"Invalid Person Number format: '{person_num_str}'. Must be a number."})
                        failed += 1
                        continue

                    if not employee_name_str:
                        errors.append({"row": row_num, "message": "Employee Name is required"})
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

                    # Handle duplicate within same file: keep the last occurrence
                    if person_num_val in seen_person_numbers:
                        # Already processed this person_number in this file; skip duplicate row within the file
                        errors.append({"row": row_num, "message": f"Duplicate Person Number {person_num_val} within the file (keeping first occurrence)"})
                        failed += 1
                        continue

                    seen_person_numbers.add(person_num_val)

                    # Upsert: update existing record or insert new one
                    if person_num_val in existing_records:
                        existing = existing_records[person_num_val]
                        existing.employee_name = employee_name_str
                        existing.email = email_str
                        updated += 1
                    else:
                        new_config = EmployeeEmailMaster(
                            person_number=person_num_val,
                            employee_name=employee_name_str,
                            email=email_str
                        )
                        db.add(new_config)
                        inserted += 1

                if inserted > 0 or updated > 0:
                    await db.commit()

                return {
                    "success": True,
                    "inserted": inserted,
                    "updated": updated,
                    "failed": failed,
                    "errors": errors
                }
            except Exception as e:
                logger.exception("Failed to import employee configuration data into database")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database import failed: {str(e)}"
                )
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in import_employee_emails_excel: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def generate_sample_excel() -> io.BytesIO:
        """Generate sample Excel bytes for Employee Configuration import template."""
        try:
            data = [
                {"Person Number": 10001234, "Employee Name": "John Doe", "Email": "johndoe@company.com"},
                {"Person Number": 10005678, "Employee Name": "Jane Smith", "Email": "janesmith@company.com"}
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
    async def delete_employee_email(id: int, db: AsyncSession) -> bool:
        """Delete an Employee configuration by ID. Returns True if deleted, False if not found."""
        try:
            res = await db.execute(select(EmployeeEmailMaster).where(EmployeeEmailMaster.id == id))
            config = res.scalar_one_or_none()
            
            if not config:
                return False
                
            await db.delete(config)
            await db.commit()
            return True
        except Exception as e:
            logger.exception(f"Failed to delete employee configuration {id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete failed: {str(e)}"
            )


    @staticmethod
    async def update_employee_email(id: int, config: EmployeeEmailUpdate, db: AsyncSession) -> EmployeeEmailMaster:
        """Update an existing Employee configuration."""
        try:
            email_str = config.email.strip().lower()
            
            email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(email_regex, email_str):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format")
            
            res = await db.execute(select(EmployeeEmailMaster).where(EmployeeEmailMaster.id == id))
            existing = res.scalar_one_or_none()
            
            if not existing:
                return None
            
            # Duplicate check: check if another record with the same person number already exists (excluding current record)
            res_dup = await db.execute(
                select(EmployeeEmailMaster)
                .where(EmployeeEmailMaster.person_number == config.person_number)
                .where(EmployeeEmailMaster.id != id)
            )
            duplicate = res_dup.scalar_one_or_none()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee with this Person Number already exists")
            
            existing.person_number = config.person_number
            existing.employee_name = config.employee_name.strip()
            existing.email = email_str
            
            await db.commit()
            return existing
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to update employee configuration {id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Update failed: {str(e)}"
            )
