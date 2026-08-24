from sqlalchemy import Column, DateTime, Index, Integer, String, func

from config.database import Base


class NdcAuthAuditLog(Base):
    __tablename__ = "ndc_auth_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True)
    performed_by = Column(String(255), nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    notes = Column(String(1000), nullable=True)

    __table_args__ = (
        Index("idx_auth_audit_email_search", "email"),
        Index("idx_auth_audit_event_search", "event_type"),
    )
