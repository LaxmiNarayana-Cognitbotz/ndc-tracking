import { X, Download } from "lucide-react";
import { NDCRecord } from "../../types";
import { StatusBadge } from "./StatusBadge";
import { exportToExcel } from "../../utils/excelExport";
import { getPendingDepartments } from "../../utils/pendingDepartments";

interface DataModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: NDCRecord[];
  onSendReminder?: (type: string) => void;
}

export function DataModal({ isOpen, onClose, title, data }: DataModalProps) {
  if (!isOpen) return null;

  const isOverdueModal = title === "Overdue Cases";

  const getDelayDays = (record: NDCRecord) => {
    if (record.ndcCompletedDate) return 0;
    const lastWorking = new Date(record.lastWorkingDate);
    const today = new Date();
    return Math.max(0, Math.ceil((today.getTime() - lastWorking.getTime()) / (1000 * 60 * 60 * 24)));
  };

  const getOverallStatus = (record: NDCRecord) => {
    const statuses = [
      record.rmApprovalStatus,
      record.itApprovalStatus,
      record.abexApprovalStatus,
      record.telecomApprovalStatus,
      record.safetyApprovalStatus,
      record.administrationApprovalStatus,
      record.securityApprovalStatus,
      record.hrApprovalStatus,
      record.gccHrApprovalStatus,
      record.finalAbexApprovalStatus,
      record.businessSpecificApprovalStatus,
      record.legatrixApprovalStatus,
    ].filter((s) => s !== "Not Applicable" && s !== "");

    if (statuses.some((s) => s === "Pending")) return "Pending";
    if (statuses.some((s) => s === "In Progress")) return "In Progress";
    if (statuses.every((s) => s === "Completed")) return "Completed";
    return "In Progress";
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-card w-screen h-screen flex flex-col border-0">
        <div className="p-6 border-b border-border flex items-center justify-between">
          <h2 className="text-2xl font-bold text-foreground">{title}</h2>
          <div className="flex items-center gap-2">
            {/* {onSendReminder && (title === "F&F Open" || title === "F&F Revision Required") && (
              <button
                disabled={data.length === 0}
                onClick={() => {
                  const type = title === "F&F Open" ? "fnf_open" : "fnf_revision";
                  onSendReminder(type);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Mail className="w-4 h-4" />
                Send Reminder
              </button>
             
            )} */}
            <button
              disabled={data.length === 0}
              onClick={() => exportToExcel(data, title || "Data_Export")}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export to Excel
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-muted rounded-[4px] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="bg-card rounded-[4px] border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Person Number</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Employee Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Department</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC Stage</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Last Working Date</th>
                    {isOverdueModal && (
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Delay Days</th>
                    )}
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Overall Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Pending Departments</th>
                    
                    {/* All Approval Stages (Status + Date) in proper order */}
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">RM Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">RM Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">IT Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">IT Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Abex Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Abex Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Telecom Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Telecom Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Store Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Store Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Safety Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Safety Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Administration Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Administration Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Security Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Security Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">HR Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">HR Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">GCC HR Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">GCC HR Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Business Specific Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Business Specific Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Final Abex Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Final Abex Approval Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Legatrix Approval</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Legatrix Approval Date</th>

                    {!isOverdueModal && (
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC Completed</th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {data.length === 0 ? (
                    <tr>
                      <td colSpan={100} className="px-4 py-8 text-center text-muted-foreground">
                        No data found
                      </td>
                    </tr>
                  ) : (
                    data.map((record) => (
                      <tr key={record.id} className="hover:bg-muted/50">
                        <td className="px-4 py-3 text-sm font-medium whitespace-nowrap">{record.personNumber}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.employeeName}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.department}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.ndcStage}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.lastWorkingDate}</td>
                        {isOverdueModal && (
                          <td className="px-4 py-3 text-sm whitespace-nowrap">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                              {getDelayDays(record)} days
                            </span>
                          </td>
                        )}
                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                          <StatusBadge status={getOverallStatus(record)} />
                        </td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                          {getPendingDepartments(record)}
                        </td>
                        
                        {/* All Approval Stages Data */}
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.rmApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.rmApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.itApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.itApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.abexApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.abexApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.telecomApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.telecomApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.storeApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.storeApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.safetyApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.safetyApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.administrationApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.administrationApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.securityApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.securityApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.hrApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.hrApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.gccHrApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.gccHrApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.businessSpecificApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.businessSpecificApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.finalAbexApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.finalAbexApprovalDate || '-'}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.legatrixApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.legatrixApprovalDate || '-'}</td>
                        {!isOverdueModal && (
                          <td className="px-4 py-3 text-sm whitespace-nowrap">
                            {record.ndcCompletedDate || (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            Total Records: {data.length}
          </div>
        </div>
      </div>
    </div>
  );
}
