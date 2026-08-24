from sqlalchemy import Column, DateTime, Integer, String, func

from config.database import Base


class EmailRecipient(Base):
    __tablename__ = "email_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    department = Column(String(200), nullable=False)
    role = Column(String(200))
    created_at = Column(DateTime, server_default=func.now())
