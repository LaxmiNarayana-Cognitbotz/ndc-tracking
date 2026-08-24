from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func

from config.database import Base


class EmployeeEmailMaster(Base):
    __tablename__ = "employee_email_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_number = Column(BigInteger, nullable=False, unique=True)
    employee_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
