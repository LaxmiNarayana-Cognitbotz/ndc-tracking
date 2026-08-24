from sqlalchemy import Column, DateTime, Integer, String, func

from config.database import Base


class RmEmailConfiguration(Base):
    __tablename__ = "rm_email_configuration"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rm_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
