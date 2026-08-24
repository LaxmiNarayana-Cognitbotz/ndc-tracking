from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func

from config.database import Base


class NdcApproval(Base):
    __tablename__ = "ndc_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ndc_record_id = Column(Integer, ForeignKey("ndc_records.id", ondelete="CASCADE"), nullable=False)
    stage_name = Column(String(100), nullable=False)
    approver_name = Column(String(200))
    status = Column(String(50))
    sequence_order = Column(Integer)
    stage_started_at = Column(DateTime)
    stage_completed_at = Column(DateTime)
    updated_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_approvals_stage", "stage_name", "status"),
        Index("idx_approvals_record", "ndc_record_id"),
    )
