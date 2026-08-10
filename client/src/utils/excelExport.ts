import * as XLSX from 'xlsx';

const headerMapping: Record<string, string> = {
  // id: "ID",
  ndcAssignedDate: "NDC Assigned Date",
  personNumber: "Person Number",
  employeeName: "Employee Name",
  department: "Department",
  ndcStage: "NDC Stage",
  pendingDepartments: "Pending Departments",
  resignationDate: "Resignation Date",
  lastWorkingDate: "Last Working Date",
  ndcInitiatedDate: "NDC Initiated Date",
  rmApprovalStatus: "RM Approval Status",
  rmApprover: "RM Approver",
  rmApprovalDate: "RM Approval Date",
  itApprovalStatus: "IT Approval Status",
  itApprover: "IT Approver",
  itApprovalDate: "IT Approval Date",
  abexApprovalStatus: "ABEX Approval Status",
  abexApprover: "ABEX Approver",
  abexApprovalDate: "ABEX Approval Date",
  telecomApprovalStatus: "Telecom Approval Status",
  telecomApprover: "Telecom Approver",
  telecomApprovalDate: "Telecom Approval Date",
  storeApprovalStatus: "Store Approval Status",
  storeApprover: "Store Approver",
  storeApprovalDate: "Store Approval Date",
  safetyApprovalStatus: "Safety Approval Status",
  safetyApprover: "Safety Approver",
  safetyApprovalDate: "Safety Approval Date",
  administrationApprovalStatus: "Administration Approval Status",
  administrationApprover: "Administration Approver",
  administrationApprovalDate: "Administration Approval Date",
  securityApprovalStatus: "Security Approval Status",
  securityApprover: "Security Approver",
  securityApprovalDate: "Security Approval Date",
  hrApprovalStatus: "HR Approval Status",
  hrApprover: "HR Approver",
  hrApprovalDate: "HR Approval Date",
  gccHrApprovalStatus: "GCC HR Approval Status",
  gccHrApprover: "GCC HR Approver",
  gccHrApprovalDate: "GCC HR Approval Date",
  finalAbexApprovalStatus: "Final ABEX Approval Status",
  finalAbexApprover: "Final ABEX Approver",
  finalAbexApprovalDate: "Final ABEX Approval Date",
  ndcCompletedDate: "NDC Completed Date",
  createdBy: "Created By",
  fnfStatus: "F&F Status",
  fnfDocument: "F&F Document",
  fnfActionDate: "F&F Action Date",
  fnfCompletedDate: "F&F Completed Date",
  recoveryPendingDept: "Recovery Pending Dept",
  recoveryAmount: "Recovery Amount",
  recoveryStatus: "Recovery Status",
  openTextNotes: "Open Text Notes"
};

export const exportToExcel = (data: any[], filename: string) => {
  const formattedData = data.map(item => {
    const formattedItem: any = {};
    for (const key in item) {
      if (key === 'id') continue; // Exclude the id field from export

      if (headerMapping[key]) {
        formattedItem[headerMapping[key]] = item[key];
      } else {
        // Fallback: capitalize the first letter and separate camelCase
        const titleCaseKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
        formattedItem[titleCaseKey] = item[key];
      }
    }
    return formattedItem;
  });

  const worksheet = XLSX.utils.json_to_sheet(formattedData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Sheet1");
  
  // Sanitize filename to prevent browser download issues with special characters (like '&')
  const sanitizedFilename = (filename || "Export").replace(/[^a-zA-Z0-9_\- ]/g, '_').trim();
  
  XLSX.writeFile(workbook, `${sanitizedFilename}.xlsx`);
};
