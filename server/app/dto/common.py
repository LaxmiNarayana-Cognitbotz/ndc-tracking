from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CommonNDCRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    id: str
    ndc_assigned_date: str
    person_number: str
    employee_name: str
    department: str
    ndc_stage: str
    resignation_date: str
    last_working_date: str
    ndc_initiated_date: str
    rm_approval_status: str
    rm_approver: str
    rm_approval_date: str
    it_approval_status: str
    it_approver: str
    it_approval_date: str
    abex_approval_status: str
    abex_approver: str
    abex_approval_date: str
    telecom_approval_status: str
    telecom_approver: str
    telecom_approval_date: str
    store_approval_status: str
    store_approver: str
    store_approval_date: str
    safety_approval_status: str
    safety_approver: str
    safety_approval_date: str
    administration_approval_status: str
    administration_approver: str
    administration_approval_date: str
    security_approval_status: str
    security_approver: str
    security_approval_date: str
    hr_approval_status: str
    hr_approver: str
    hr_approval_date: str
    gcc_hr_approval_status: str
    gcc_hr_approver: str
    gcc_hr_approval_date: str
    final_abex_approval_status: str
    final_abex_approver: str
    final_abex_approval_date: str
    business_specific_approval_status: str = "Not Applicable"
    business_specific_approver: str = ""
    business_specific_approval_date: str = ""
    legatrix_approval_status: str = "Not Applicable"
    legatrix_approver: str = ""
    legatrix_approval_date: str = ""
    ndc_completed_date: str
    created_by: str
    fnf_status: str
    fnf_document: str
    fnf_action_date: str
    fnf_completed_date: str
    is_fnf_completed: bool = False
    is_fnf_closed: bool = False
    is_fnf_revision: bool = False
    gcc_initiate_date: str = ""
    fnf_document_count: int = 0
    fnf_revision_start_date: str = ""
    fnf_revision_completed_date: str = ""
    fnf_revision_comment: str = ""
    recovery_pending_dept: str
    recovery_amount: float
    recovery_status: str
    open_text_notes: str


class FnfUpdateRequest(BaseModel):
    is_fnf_completed: Optional[bool] = None
    is_fnf_closed: Optional[bool] = None
    is_fnf_revision: Optional[bool] = None
    fnf_document_count: Optional[int] = None
    fnf_revision_comment: Optional[str] = None
