import { useState } from "react";
import { NDCRecord } from "../../types";
import { StatusBadge } from "./StatusBadge";
import { getPendingDepartments } from "../../utils/pendingDepartments";
import { ChevronLeft, ChevronRight, Download, Settings } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Checkbox } from "../ui/checkbox";
import { Label } from "../ui/label";

interface NDCTableProps {
  data: NDCRecord[];
  currentPage: number;
  setCurrentPage: (page: number) => void;
  itemsPerPage: number;
  onSort: (column: keyof NDCRecord) => void;
  getRowHighlight: (record: NDCRecord) => string;
  onExport: (visibleColumns: {key: string, label: string}[]) => void;
}

const allColumns = [
  { key: "ndcAssignedDate", label: "NDC Assigned Date", sortable: true },
  { key: "personNumber", label: "Person Number", sortable: true },
  { key: "employeeName", label: "Name", sortable: true },
  { key: "department", label: "Department", sortable: true },
  { key: "ndcStage", label: "NDC Stage", sortable: false },
  { key: "pendingDepartments", label: "Pending Departments", sortable: false },
  { key: "resignationDate", label: "Resignation Date", sortable: false },
  { key: "lastWorkingDate", label: "Last Working Date", sortable: false },
  { key: "ndcInitiatedDate", label: "NDC Initiated Date", sortable: true },
  { key: "rmApprovalStatus", label: "RM Approval", sortable: false },
  { key: "rmApprovalDate", label: "RM Approval Date", sortable: false },
  { key: "itApprovalStatus", label: "IT Approval", sortable: false },
  { key: "itApprovalDate", label: "IT Approval Date", sortable: false },
  { key: "abexApprovalStatus", label: "Abex Approval", sortable: false },
  { key: "abexApprovalDate", label: "Abex Approval Date", sortable: false },
  { key: "telecomApprovalStatus", label: "Telecom Approval", sortable: false },
  { key: "telecomApprovalDate", label: "Telecom Approval Date", sortable: false },
  { key: "storeApprovalStatus", label: "Store Approval", sortable: false },
  { key: "storeApprovalDate", label: "Store Approval Date", sortable: false },
  { key: "safetyApprovalStatus", label: "Safety Approval", sortable: false },
  { key: "safetyApprovalDate", label: "Safety Approval Date", sortable: false },
  { key: "administrationApprovalStatus", label: "Administration Approval", sortable: false },
  { key: "administrationApprovalDate", label: "Administration Approval Date", sortable: false },
  { key: "securityApprovalStatus", label: "Security Approval", sortable: false },
  { key: "securityApprovalDate", label: "Security Approval Date", sortable: false },
  { key: "hrApprovalStatus", label: "HR Approval", sortable: false },
  { key: "hrApprovalDate", label: "HR Approval Date", sortable: false },
  { key: "gccHrApprovalStatus", label: "GCC HR Approval", sortable: false },
  { key: "gccHrApprovalDate", label: "GCC HR Approval Date", sortable: false },
  { key: "finalAbexApprovalStatus", label: "Final Abex Approval", sortable: false },
  { key: "finalAbexApprovalDate", label: "Final Abex Approval Date", sortable: false },
  { key: "businessSpecificApprovalStatus", label: "Business Specific Approval", sortable: false },
  { key: "businessSpecificApprovalDate", label: "Business Specific Approval Date", sortable: false },
  { key: "legatrixApprovalStatus", label: "Legatrix Approval", sortable: false },
  { key: "legatrixApprovalDate", label: "Legatrix Approval Date", sortable: false },
  { key: "ndcCompletedDate", label: "NDC Completed", sortable: false },
];

export function NDCTable({
  data,
  currentPage,
  setCurrentPage,
  itemsPerPage,
  onSort,
  getRowHighlight,
  onExport,
}: NDCTableProps) {
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(
    new Set(["storeApprovalStatus", "storeApprovalDate"])
  );

  const totalPages = Math.ceil(data.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = data.slice(startIndex, startIndex + itemsPerPage);

  const visibleColumns = allColumns.filter((col) => !hiddenColumns.has(col.key));

  const toggleColumn = (columnKey: string) => {
    setHiddenColumns((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(columnKey)) {
        newSet.delete(columnKey);
      } else {
        newSet.add(columnKey);
      }
      return newSet;
    });
  };

  const renderCellValue = (record: NDCRecord, columnKey: string) => {
    const value = record[columnKey as keyof NDCRecord];

    if (columnKey === "pendingDepartments") {
      return getPendingDepartments(record);
    }

    if (columnKey.includes("ApprovalStatus")) {
      return <StatusBadge status={value as string} />;
    }

    if (columnKey === "fnfStatus") {
      if (!value) return <span className="text-muted-foreground">-</span>;
      const colorMap: Record<string, string> = {
        "Closed": "text-teal-600 bg-teal-50 px-2 py-1 rounded-[4px]",
        "Done": "text-green-600 bg-green-50 px-2 py-1 rounded-[4px]",
        "Open": "text-blue-600 bg-blue-50 px-2 py-1 rounded-[4px]",
        "Revision Required": "text-red-600 bg-red-50 px-2 py-1 rounded-[4px]",
      };
      return <span className={colorMap[value as string] || ""}>{value as string}</span>;
    }

    if (columnKey === "recoveryStatus") {
      if (!value) return <span className="text-muted-foreground">-</span>;
      const colorMap: Record<string, string> = {
        "Pending": "text-orange-600",
        "Completed": "text-green-600",
      };
      return <span className={colorMap[value as string] || ""}>{value as string}</span>;
    }

    if (!value) return <span className="text-muted-foreground">-</span>;
    return value as string;
  };

  return (
    <div className="bg-card rounded-[4px] border border-border overflow-hidden">
      <div className="p-6 border-b border-border flex items-center justify-between">
        <h2 className="text-xl font-bold">NDC Records</h2>
        <div className="flex gap-2">
          <Popover>
            <PopoverTrigger asChild>
              <button className="flex items-center gap-2 px-4 py-2 bg-muted text-foreground rounded-[4px] hover:bg-muted/80 transition-colors">
                <Settings className="w-4 h-4" />
                Columns
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80 max-h-96 overflow-y-auto">
              <div className="space-y-2">
                <h4 className="font-semibold mb-3">Show/Hide Columns</h4>
                {allColumns.map((col) => (
                  <div key={col.key} className="flex items-center space-x-2">
                    <Checkbox
                      id={col.key}
                      checked={!hiddenColumns.has(col.key)}
                      onCheckedChange={() => toggleColumn(col.key)}
                    />
                    <Label htmlFor={col.key} className="text-sm cursor-pointer">
                      {col.label}
                    </Label>
                  </div>
                ))}
              </div>
            </PopoverContent>
          </Popover>
          <button
            onClick={() => onExport(visibleColumns)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 transition-colors"
          >
            <Download className="w-4 h-4" />
            Export to Excel
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted sticky top-0">
            <tr>
              {visibleColumns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && onSort(col.key as keyof NDCRecord)}
                  className={`px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide whitespace-nowrap ${
                    col.sortable ? "cursor-pointer hover:bg-muted/80" : ""
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {paginatedData.map((record) => (
              <tr key={record.id} className={`hover:bg-muted/50 ${getRowHighlight(record)}`}>
                {visibleColumns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-sm whitespace-nowrap">
                    {renderCellValue(record, col.key)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-4 border-t border-border flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, data.length)} of{" "}
          {data.length} records
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
