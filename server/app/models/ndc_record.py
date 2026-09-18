from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    func,
)

from config.database import Base


class NdcRecord(Base):
    __tablename__ = "ndc_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_number = Column(BigInteger, nullable=False, unique=True)
    employee_name = Column(String(200), nullable=False)
    business_unit = Column(String(200))
    legal_employer = Column(String(200))
    location = Column(String(200))
    location_city = Column(String(100))
    department = Column(String(300))
    department_reporting_name = Column(String(200))
    ndc_stage = Column(String(50))
    resignation_date = Column(Date)
    last_working_date = Column(Date)
    ndc_assigned_date = Column(Date)
    ndc_initiated_date = Column(Date)
    ndc_completed_date = Column(Date)
    created_by = Column(String(200))
    source_file = Column(String(500))
    batch_id = Column(Integer)
    
    # F&F tracking columns
    is_fnf_completed = Column(Boolean, default=False, nullable=False, server_default="false")
    is_fnf_closed = Column(Boolean, default=False, nullable=False, server_default="false")
    is_fnf_revision = Column(Boolean, default=False, nullable=False, server_default="false")
    is_fnf_email_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    is_fnf_revision_email_sent = Column(Boolean, default=False, nullable=False, server_default="false")
    # True when finance has paid but DMS/SharePoint document upload is still pending
    is_fnf_paid = Column(Boolean, default=False, nullable=False, server_default="false")
    fnf_completed_date = Column(Date, nullable=True)
    gcc_initiate_date = Column(Date, nullable=True)
    fnf_document_count = Column(Integer, default=0, nullable=False, server_default="0")
    fnf_revision_start_date = Column(Date, nullable=True)
    fnf_revision_completed_date = Column(Date, nullable=True)
    fnf_revision_comment = Column(String(1000), nullable=True)

    # Department Approval Dates
    rm_approval_date = Column(Date, nullable=True)
    it_approval_date = Column(Date, nullable=True)
    abex_approval_date = Column(Date, nullable=True)
    telecom_approval_date = Column(Date, nullable=True)
    store_approval_date = Column(Date, nullable=True)
    safety_approval_date = Column(Date, nullable=True)
    administration_approval_date = Column(Date, nullable=True)
    security_approval_date = Column(Date, nullable=True)
    hr_approval_date = Column(Date, nullable=True)
    gcc_hr_approval_date = Column(Date, nullable=True)
    final_abex_approval_date = Column(Date, nullable=True)
    business_specific_approval_date = Column(Date, nullable=True)
    legatrix_approval_date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "ndc_stage IN ('Recovery Pending', 'GCC Pending', 'NDC Completed')",
            name="chk_stage",
        ),
        Index("idx_ndc_stage", "ndc_stage"),
        Index("idx_business_unit", "business_unit"),
        Index("idx_location_city", "location_city"),
        Index("idx_ndc_initiated", "ndc_initiated_date"),
    )
