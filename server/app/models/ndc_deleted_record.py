from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func

from config.database import Base


class NdcDeletedRecord(Base):
    __tablename__ = "ndc_deleted_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_number = Column(BigInteger, unique=True, nullable=False, index=True)
    employee_name = Column(String(200), nullable=True)
    deleted_by = Column(String(200), nullable=False)
    deleted_at = Column(DateTime, server_default=func.now())
    reason = Column(String(500), nullable=True)
