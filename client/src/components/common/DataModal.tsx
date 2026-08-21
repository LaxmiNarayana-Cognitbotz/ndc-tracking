import { useState } from "react";
import { X, Download, ChevronLeft, ChevronRight } from "lucide-react";
import { NDCRecord } from "../../types";
import { StatusBadge } from "./StatusBadge";
import { exportToExcel } from "../../utils/excelExport";
import { getPendingDepartments } from "../../utils/pendingDepartments";
import { formatDate } from "../../utils/dateFormatter";

interface DataModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: NDCRecord[];
  onSendReminder?: (type: string) => void;
}

export function DataModal({ isOpen, onClose, title, data }: DataModalProps) {
  if (!isOpen) return null;

  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);

  const totalPages = Math.max(1, Math.ceil(data.length / itemsPerPage));
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = data.slice(startIndex, startIndex + itemsPerPage);

  const isOverdueModal = title === "Overdue Cases" || title === "NDC Overdue after Exit Cases" || title.includes("Overdue");

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
      <div className="bg-card border border-border rounded-[4px] shadow-xl w-full max-w-7xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">
            {title} ({data.length})
          </h2>
          <div className="flex items-center gap-2">
            <button
              disabled={data.length === 0}
              onClick={() => exportToExcel(data, title.replace(/ /g, "_"))}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-muted hover:bg-accent text-foreground text-xs rounded-[4px] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-[4px] hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="border border-border rounded-[4px] overflow-hidden">
            <div className="max-h-[60vh] overflow-y-auto">
              <table className="w-full text-xs">
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
                    paginatedData.map((record) => (
                      <tr key={record.id} className="hover:bg-muted/50">
                        <td className="px-4 py-3 text-sm font-medium whitespace-nowrap">{record.personNumber}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.employeeName}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.department}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{record.ndcStage}</td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.lastWorkingDate)}</td>
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
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.rmApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.rmApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.itApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.itApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.abexApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.abexApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.telecomApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.telecomApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.storeApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.storeApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.safetyApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.safetyApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.administrationApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.administrationApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.securityApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.securityApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.hrApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.hrApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.gccHrApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.gccHrApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.businessSpecificApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.businessSpecificApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.finalAbexApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.finalAbexApprovalDate)}</td>
                        
                        <td className="px-4 py-3 text-sm whitespace-nowrap"><StatusBadge status={record.legatrixApprovalStatus} /></td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.legatrixApprovalDate)}</td>
                        {!isOverdueModal && (
                          <td className="px-4 py-3 text-sm whitespace-nowrap">
                            {formatDate(record.ndcCompletedDate)}
                          </td>
                        )}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          {data.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="text-sm text-muted-foreground">
                  Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, data.length)} of {data.length} records
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Rows per page:</span>
                  <select
                    value={itemsPerPage}
                    onChange={(e) => {
                      setItemsPerPage(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="h-8 px-2 rounded-[4px] border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                  >
                    <option value={20}>20</option>
                    <option value={30}>30</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
