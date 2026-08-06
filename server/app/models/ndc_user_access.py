from sqlalchemy import Column, DateTime, Index, Integer, String, func

from config.database import Base


class NdcUserAccess(Base):
    __tablename__ = "ndc_user_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255))
    role = Column(String(50), nullable=False, default="admin")
    status = Column(String(50), nullable=False, default="pending")
    hashed_password = Column(String(255), nullable=True)
    approval_token = Column(String(255), unique=True, nullable=True)
    reset_token = Column(String(255), unique=True, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    otp_code = Column(String(10), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    requested_at = Column(DateTime, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    notes = Column(String(1000), nullable=True)

    __table_args__ = (
        Index("idx_user_access_email_search", "email"),
        Index("idx_user_access_token_search", "approval_token"),
        Index("idx_user_access_reset_token_search", "reset_token"),
    )
