import { useState, useMemo, useEffect } from "react";
import { NDCRecord } from "../../types";
import axios from "../../lib/axios";
import { exportToExcel } from "../../utils/excelExport";
import { createPPT, addImageSlide } from "../../utils/pptExport";
import { PPTDownloadButton } from "../../components/common/PPTDownloadButton";
import { toast } from "sonner";
import { KPICard } from "../../components/common/KPICard";
import { FilterBar } from "./components/FilterBar";
import { DataModal } from "../../components/common/DataModal";
import { NDCTable } from "../../components/common/NDCTable";
import { FullScreenModal } from "../../components/common/FullScreenModal";
import { LoadingScreen } from "../../components/common/LoadingScreen";
import { getPendingDepartments } from "../../utils/pendingDepartments";
import { formatDate, parseDate } from "../../utils/dateFormatter";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "../../components/ui/popover";
import { Calendar } from "../../components/ui/calendar";
import { format } from "date-fns";
import { type DateRange } from "react-day-picker";
import {
  Users,
  ChevronLeft,
  ChevronRight,

  CheckCircle,
  Clock,
  AlertCircle,
  TrendingUp,
  Building2,
  XCircle,
  Download,

  FolderOpen,
  CalendarIcon,
  Mail,
  AlertTriangle,
  Send,
} from "lucide-react";

export function Overview() {
  const [mockNDCData, setMockNDCData] = useState<NDCRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [ndcStageFilter, setNdcStageFilter] = useState("");
  const [approvalDepartmentFilter, setApprovalDepartmentFilter] = useState("");
  const [approvalStatusFilter, setApprovalStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColumn, setSortColumn] = useState<keyof NDCRecord | "">("");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [modalOpen, setModalOpen] = useState(false);
  const [modalData, setModalData] = useState<{ title: string; data: NDCRecord[] }>({ title: "", data: [] });
  const [openNDCModalOpen, setOpenNDCModalOpen] = useState(false);
  const [closedNDCModalOpen, setClosedNDCModalOpen] = useState(false);
  const [ndcDelayedTableOpen, setNdcDelayedTableOpen] = useState(false);
  const [totalExitModalOpen, setTotalExitModalOpen] = useState(false);
  const [inProgressModalOpen, setInProgressModalOpen] = useState(false);
  const [pendingApprovalModalOpen, setPendingApprovalModalOpen] = useState(false);
  const [overdueModalOpen, setOverdueModalOpen] = useState(false);

  // Super Admin Delete Employee State
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [recordToDelete, setRecordToDelete] = useState<NDCRecord | null>(null);
  const [deleteReason, setDeleteReason] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteRecord = (record: NDCRecord) => {
    setRecordToDelete(record);
    setDeleteReason("");
    setDeleteConfirmOpen(true);
  };

  const confirmDeleteRecord = async () => {
    if (!recordToDelete) return;
    setIsDeleting(true);
    const toastId = toast.loading(`Deleting employee ${recordToDelete.employeeName}...`);
    try {
      const url = `/api/admin/ndc-records/${recordToDelete.personNumber}${deleteReason ? `?reason=${encodeURIComponent(deleteReason)}` : ""}`;
      await axios.delete(url);
      toast.dismiss(toastId);
      toast.success(`Employee ${recordToDelete.employeeName} (${recordToDelete.personNumber}) permanently deleted.`);
      setMockNDCData((prev) => prev.filter((r) => r.personNumber !== recordToDelete.personNumber));
      setDeleteConfirmOpen(false);
      setRecordToDelete(null);
    } catch (err: any) {
      toast.dismiss(toastId);
      const detail = err?.response?.data?.detail || err?.message || "Failed to delete record";
      toast.error(`Delete failed: ${detail}`);
    } finally {
      setIsDeleting(false);
    }
  };
  
  const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined);
  const [appliedDateRange, setAppliedDateRange] = useState<DateRange | undefined>(undefined);
  const [popoverOpen, setPopoverOpen] = useState(false);
  
  const [monthLeft, setMonthLeft] = useState<Date>(new Date());
  const [monthRight, setMonthRight] = useState<Date>(() => {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() + 1);
    return d;
  });

  const handleMonthLeftChange = (newMonth: Date) => {
    setMonthLeft(newMonth);
    if (newMonth.getTime() >= monthRight.getTime()) {
      const next = new Date(newMonth);
      next.setMonth(next.getMonth() + 1);
      setMonthRight(next);
    }
  };

  const handleMonthRightChange = (newMonth: Date) => {
    setMonthRight(newMonth);
    if (newMonth.getTime() <= monthLeft.getTime()) {
      const prev = new Date(newMonth);
      prev.setMonth(prev.getMonth() - 1);
      setMonthLeft(prev);
    }
  };

  const [ndcDelayedCurrentPage, setNdcDelayedCurrentPage] = useState(1);
  const [sendingReminder, setSendingReminder] = useState(false);
  const [reminderMailDialogOpen, setReminderMailDialogOpen] = useState(false);
  const [reminderMailEmailTo, setReminderMailEmailTo] = useState("");
  const [reminderMailType, setReminderMailType] = useState<string>("ndc_delayed");
  const itemsPerPage = 20;

  useEffect(() => {
    setIsLoading(true);
    let url = "/api/v1/ndc-records";
    if (appliedDateRange?.from) {
      const startStr = format(appliedDateRange.from, "yyyy-MM-dd");
      const endStr = appliedDateRange.to ? format(appliedDateRange.to, "yyyy-MM-dd") : startStr;
      url += `?start_date=${startStr}&end_date=${endStr}`;
    }
    axios.get(url).then((res) => {
      const data = res.data?.data || res.data;
      setMockNDCData(Array.isArray(data) ? data : []);
      setIsLoading(false);
    }).catch(() => setIsLoading(false));
  }, [appliedDateRange]);

  const ndcStages = useMemo(() => {
    return Array.from(new Set(mockNDCData.map((record) => record.ndcStage))).sort();
  }, [mockNDCData]);

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

  const isOverdue = (record: NDCRecord) => {
    if (record.ndcStage === "NDC Completed") return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const lwd = new Date(record.lastWorkingDate);
    lwd.setHours(0, 0, 0, 0);
    return lwd < today;
  };

  const getDelayedDays = (record: NDCRecord) => {
    if (record.ndcStage === "NDC Completed") return 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const lwd = new Date(record.lastWorkingDate);
    lwd.setHours(0, 0, 0, 0);
    const diff = today.getTime() - lwd.getTime();
    return diff > 0 ? Math.ceil(diff / (1000 * 60 * 60 * 24)) : 0;
  };

  // Top Delayed Cases: NDC not cleared within LWD + 30 days, at any stage
  const isTopDelayed = (record: NDCRecord) => getDelayedDays(record) > 30;

  const applyApprovalFilters = (filtered: NDCRecord[]) => {
    const normalize = (str: string) => (str || "").toLowerCase().replace(/[_\s]+/g, "");

    const isITOrSecDepartment = (dept: string) => {
      const norm = normalize(dept);
      return norm === "it" || norm === "security";
    };

    const isLWDWithin3Days = (record: NDCRecord) => {
      const lwd = parseDate(record.lastWorkingDate);
      if (!lwd) return false;
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      lwd.setHours(0, 0, 0, 0);
      const daysUntilLWD = Math.round((lwd.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
      return daysUntilLWD <= 3;
    };

    if (approvalDepartmentFilter && approvalStatusFilter) {
      const statusMap: Record<string, string> = {
        'rm': 'rmApprovalStatus', 'it': 'itApprovalStatus', 'abex': 'abexApprovalStatus',
        'telecom': 'telecomApprovalStatus', 'store': 'storeApprovalStatus', 'safety': 'safetyApprovalStatus',
        'administration': 'administrationApprovalStatus', 'security': 'securityApprovalStatus',
        'hr': 'hrApprovalStatus', 'gcchr': 'gccHrApprovalStatus', 'finalabex': 'finalAbexApprovalStatus',
        'businessspecific': 'businessSpecificApprovalStatus', 'legatrix': 'legatrixApprovalStatus'
      };
      const fieldName = statusMap[normalize(approvalDepartmentFilter)] as keyof NDCRecord;
      const targetStatus = normalize(approvalStatusFilter);
      const isITOrSec = isITOrSecDepartment(approvalDepartmentFilter);

      return filtered.filter((r) => {
        if (!fieldName) return false;
        const status = normalize(r[fieldName] as string);
        if (status !== targetStatus) return false;
        if (targetStatus === "pending" && isITOrSec) {
          return isLWDWithin3Days(r);
        }
        return true;
      });
    } else if (approvalDepartmentFilter) {
      const statusMap: Record<string, string> = {
        'rm': 'rmApprovalStatus', 'it': 'itApprovalStatus', 'abex': 'abexApprovalStatus',
        'telecom': 'telecomApprovalStatus', 'store': 'storeApprovalStatus', 'safety': 'safetyApprovalStatus',
        'administration': 'administrationApprovalStatus', 'security': 'securityApprovalStatus',
        'hr': 'hrApprovalStatus', 'gcchr': 'gccHrApprovalStatus', 'finalabex': 'finalAbexApprovalStatus',
        'businessspecific': 'businessSpecificApprovalStatus', 'legatrix': 'legatrixApprovalStatus'
      };
      const fieldName = statusMap[normalize(approvalDepartmentFilter)] as keyof NDCRecord;
      const isITOrSec = isITOrSecDepartment(approvalDepartmentFilter);

      return filtered.filter((r) => {
        if (!fieldName || !r[fieldName]) return false;
        const status = normalize(r[fieldName] as string);
        if (status === "notapplicable") return false;
        if (status === "pending" && isITOrSec) {
          return isLWDWithin3Days(r);
        }
        return true;
      });
    } else if (approvalStatusFilter) {
      const targetStatus = normalize(approvalStatusFilter);
      return filtered.filter((r) => {
        const deptKeys: { key: keyof NDCRecord; isITOrSec: boolean }[] = [
          { key: "rmApprovalStatus", isITOrSec: false },
          { key: "itApprovalStatus", isITOrSec: true },
          { key: "abexApprovalStatus", isITOrSec: false },
          { key: "telecomApprovalStatus", isITOrSec: false },
          { key: "storeApprovalStatus", isITOrSec: false },
          { key: "safetyApprovalStatus", isITOrSec: false },
          { key: "administrationApprovalStatus", isITOrSec: false },
          { key: "securityApprovalStatus", isITOrSec: true },
          { key: "hrApprovalStatus", isITOrSec: false },
          { key: "gccHrApprovalStatus", isITOrSec: false },
          { key: "finalAbexApprovalStatus", isITOrSec: false },
          { key: "businessSpecificApprovalStatus", isITOrSec: false },
          { key: "legatrixApprovalStatus", isITOrSec: false },
        ];
        return deptKeys.some(({ key, isITOrSec }) => {
          const status = normalize(r[key] as string);
          if (status !== targetStatus) return false;
          if (targetStatus === "pending" && isITOrSec) {
            return isLWDWithin3Days(r);
          }
          return true;
        });
      });
    }
    return filtered;
  };

  const filteredData = useMemo(() => {
    let filtered = mockNDCData;
    if (ndcStageFilter) filtered = filtered.filter((r) => r.ndcStage === ndcStageFilter);
    filtered = applyApprovalFilters(filtered);
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (r) => r.employeeName.toLowerCase().includes(query) || r.personNumber.toLowerCase().includes(query)
      );
    }
    // Date filter removed from here because API handles it
    return filtered;
  }, [mockNDCData, ndcStageFilter, approvalDepartmentFilter, approvalStatusFilter, searchQuery]);

  const sortedData = useMemo(() => {
    if (!sortColumn) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortColumn] ?? "";
      const bValue = b[sortColumn] ?? "";
      if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
      if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortColumn, sortDirection]);

  const kpis = useMemo(() => {
    const base = mockNDCData;

    const totalNDC = base.length;
    const closedCases = base.filter((r) => r.ndcStage === "NDC Completed");
    const closedNDC = closedCases.length;
    const openNDC = base.filter((r) => ["Recovery Pending", "GCC Pending"].includes(r.ndcStage)).length;

    const recoveryPending = base.filter((r) => r.ndcStage === "Recovery Pending").length;
    const ndcPendingGCC = base.filter((r) => r.ndcStage === "GCC Pending").length;

    const overdueCases = base.filter(isOverdue);
    const overdue = overdueCases.length;
    const topDelayedCases = base.filter(isTopDelayed);
    const totalDelayed = topDelayedCases.length;

    const delayed7to30 = base.filter((r) => { const d = getDelayedDays(r); return d >= 7 && d <= 30; }).length;
    const delayedOver30 = base.filter((r) => getDelayedDays(r) > 30).length;


    const closedFnfClosed = closedCases.filter((r) => r.isFnfClosed).length;
    const closedFnfDone = closedCases.filter((r) => r.isFnfCompleted).length;
    const closedFnfOpen = closedCases.filter((r) => !r.isFnfCompleted && !r.isFnfRevision).length;
    const closedFnfRevision = closedCases.filter((r) => r.isFnfRevision).length;

    const inProgress = recoveryPending;
    const pendingApproval = ndcPendingGCC;

    // Average completion time (days from ndcInitiatedDate to ndcCompletedDate for closed cases)
    const completedWithDates = closedCases.filter((r) => r.ndcCompletedDate && r.ndcInitiatedDate);
    const avgCompletionDays = completedWithDates.length > 0
      ? Number((
        completedWithDates.reduce((sum, r) => {
          const completed = new Date(r.ndcCompletedDate);
          const started = new Date(r.ndcInitiatedDate);
          return sum + Math.max(0, (completed.getTime() - started.getTime()) / (1000 * 60 * 60 * 24));
        }, 0) / completedWithDates.length
      ).toFixed(1))
      : 0;

    return {
      totalNDC, openNDC, closedNDC, recoveryPending, ndcPendingGCC,
      delayed7to30, delayedOver30, totalDelayed,
      closedFnfClosed, closedFnfDone, closedFnfOpen, closedFnfRevision,
      inProgress, pendingApproval, overdue, avgCompletionDays,
    };
  }, [mockNDCData]);

  const handleSort = (column: any) => {
    const col = column as keyof NDCRecord;
    if (sortColumn === col) setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    else { setSortColumn(col); setSortDirection("asc"); }
  };

  const getRowHighlight = (record: NDCRecord) => {
    const status = getOverallStatus(record);
    if (status === "Pending") return "bg-red-50";
    if (status === "Completed") return "bg-green-50";
    return "";
  };

  const FullScreenTable = ({ data, title }: { data: NDCRecord[]; title: string }) => {
    const [page, setPage] = useState(1);
    const totalPages = Math.max(1, Math.ceil(data.length / itemsPerPage));
    const startIndex = (page - 1) * itemsPerPage;
    const paginatedData = data.slice(startIndex, startIndex + itemsPerPage);

    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-border flex items-center justify-between shrink-0 bg-card">
          <h3 className="font-semibold text-foreground">{title} ({data.length})</h3>
          <button
            disabled={data.length === 0}
            onClick={() => {
              const mappedData = data.map(r => ({
                "Person No.": r.personNumber,
                "Name": r.employeeName,
                "Department": r.department,
                "Last Working Date": r.lastWorkingDate,
                "NDC Stage": r.ndcStage,
                "Pending Departments": getPendingDepartments(r),
              }));
              exportToExcel(mappedData, title || "Export");
            }}
            className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Download className="w-3 h-3" />
            Export
          </button>
        </div>
        <div className="overflow-x-auto overflow-y-auto flex-1">
          <table className="w-full text-sm">
            <thead className="bg-muted sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Person No.</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Department</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Last Working Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC Stage</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Pending Departments</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {paginatedData.map((r) => (
                <tr key={r.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3 whitespace-nowrap font-medium">{r.personNumber}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{r.employeeName}</td>
                  <td className="px-4 py-3">{r.department}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{formatDate(r.lastWorkingDate)}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{r.ndcStage}</td>
                  <td className="px-4 py-3 whitespace-nowrap">{getPendingDepartments(r)}</td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No records found</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {data.length > 0 && (
          <div className="px-6 py-4 border-t border-border flex items-center justify-between shrink-0 bg-card">
            <div className="text-sm text-muted-foreground">
              Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, data.length)} of {data.length} records
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    )
  };

  if (isLoading) return <LoadingScreen />;

  const handleDownloadPPT = async () => {
    const pptx = createPPT("Overview Dashboard");
    await addImageSlide(pptx, "KPI Summary", "section-kpi-all");

    // const headers = ["Person Number", "Name", "Department", "Last Working Date", "NDC Stage", "Status"];
    // const rows = sortedData.map(r => [
    //   r.personNumber,
    //   r.employeeName,
    //   r.department,
    //   r.lastWorkingDate,
    //   r.ndcStage,
    //   getOverallStatus(r)
    // ]);
    // 
    // addTableSlide(pptx, "NDC Records", headers, rows);
    await pptx.writeFile({ fileName: "Overview_Dashboard.pptx" });
  };

  return (
    <div className="p-8 space-y-6 h-full flex flex-col bg-background overflow-hidden relative">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">HR NDC Tracking Dashboard</h1>
          <p className="text-muted-foreground mt-2">No Dues Certificate Management System</p>
        </div>
        <div className="flex items-center gap-3">
          <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
            <PopoverTrigger asChild>
              <button className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-[4px] hover:bg-muted transition-colors text-sm font-medium whitespace-nowrap">
                <CalendarIcon className="w-4 h-4 text-muted-foreground shrink-0" />
                <span>
                  {appliedDateRange?.from
                    ? appliedDateRange.to
                      ? `${format(appliedDateRange.from, "dd MMM yyyy")} – ${format(appliedDateRange.to, "dd MMM yyyy")}`
                      : format(appliedDateRange.from, "dd MMM yyyy")
                    : "Select Date Range"}
                </span>
                {appliedDateRange?.from && (
                  <span
                    role="button"
                    onClick={(e) => { e.stopPropagation(); setDateRange(undefined); setAppliedDateRange(undefined); }}
                    className="ml-1 text-muted-foreground hover:text-foreground cursor-pointer"
                  >
                    ✕
                  </span>
                )}
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end" sideOffset={8}>
              <div className="flex">
                {/* ─── Calendar ─── */}
                <div className="flex flex-col">
                  <div className="px-3 py-2 border-b border-border bg-muted/10 flex items-center justify-between">
                    <span className="text-xs font-semibold text-muted-foreground">Select Date Range</span>
                    {dateRange?.from && (
                      <button
                        onClick={() => { setDateRange(undefined); setAppliedDateRange(undefined); }}
                        className="text-xs text-red-500 hover:text-red-700 font-semibold cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                  <div className="flex">
                    <Calendar
                      mode="range"
                      month={monthLeft}
                      onMonthChange={handleMonthLeftChange}
                      selected={dateRange}
                      onSelect={setDateRange}
                      numberOfMonths={1}
                      showOutsideDays={false}
                      captionLayout="dropdown-buttons"
                      fromYear={2020}
                      toYear={new Date().getFullYear() + 3}
                    />
                    <Calendar
                      mode="range"
                      month={monthRight}
                      onMonthChange={handleMonthRightChange}
                      selected={dateRange}
                      onSelect={setDateRange}
                      numberOfMonths={1}
                      showOutsideDays={false}
                      captionLayout="dropdown-buttons"
                      fromYear={2020}
                      toYear={new Date().getFullYear() + 3}
                    />
                  </div>
                  <div className="px-3 py-2 border-t border-border bg-muted/10 flex justify-end">
                    <button
                      onClick={() => {
                        setAppliedDateRange(dateRange);
                        setPopoverOpen(false);
                      }}
                      className="px-4 py-1.5 bg-primary text-primary-foreground text-xs font-semibold rounded hover:bg-primary/90 transition-colors"
                    >
                      Apply Filter
                    </button>
                  </div>
                </div>
              </div>
            </PopoverContent>
          </Popover>
          <PPTDownloadButton onDownload={handleDownloadPPT} />
          {/* <button
            onClick={() => toast.info("Syncing data from OpenText...")}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Sync
          </button> */}
        </div>
      </div>

      {/* All KPIs wrapper for PPT export */}
      <div id="section-kpi-all" className="space-y-6">
        {/* Row 1: Main KPI cards */}
        <div id="section-kpi-row1" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div onClick={() => setTotalExitModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Total Employee Exit" value={kpis.totalNDC} icon={Users} colorClass="text-primary" bgClass="bg-primary/10" />
          </div>
          <div onClick={() => setOpenNDCModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Open NDC" value={kpis.openNDC} icon={FolderOpen} colorClass="text-orange-600" bgClass="bg-orange-50" />
          </div>
          <div onClick={() => setClosedNDCModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Closed NDC" value={kpis.closedNDC} icon={CheckCircle} colorClass="text-green-600" bgClass="bg-green-50" />
          </div>
          <div onClick={() => setNdcDelayedTableOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Top Delayed Cases" value={kpis.totalDelayed} icon={AlertCircle} colorClass="text-red-600" bgClass="bg-red-50" />
          </div>
        </div>

        {/* Row 2: Status KPI cards */}
        <div id="section-kpi-row2" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div onClick={() => setInProgressModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Pending NDC with departments" value={kpis.inProgress} icon={Clock} colorClass="text-yellow-600" bgClass="bg-yellow-50" />
          </div>
          <div onClick={() => setPendingApprovalModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="Pending NDC with GCC" value={kpis.pendingApproval} icon={AlertTriangle} colorClass="text-orange-600" bgClass="bg-orange-50" />
          </div>
          <div onClick={() => setOverdueModalOpen(true)} className="cursor-pointer hover:scale-105 transition-transform duration-200">
            <KPICard title="NDC Overdue after Exit" value={kpis.overdue} icon={XCircle} colorClass="text-red-700" bgClass="bg-red-100" />
          </div>
          <KPICard
            title="Avg Completion Time"
            value={`${kpis.avgCompletionDays} days`}
            icon={TrendingUp}
            colorClass="text-purple-600"
            bgClass="bg-purple-50"
          />
        </div>
      </div>

      <DataModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={modalData.title}
        data={modalData.data}
        onSendReminder={(type) => {
          setReminderMailEmailTo("");
          setReminderMailType(type);
          setReminderMailDialogOpen(true);
        }}
      />

      {/* Total Employee Exit Count Modal */}
      <FullScreenModal open={totalExitModalOpen} onClose={() => setTotalExitModalOpen(false)} title="Total Employee Exit">
        <FullScreenTable data={mockNDCData} title="All Exit Records" />
      </FullScreenModal>

      {/* Open NDC Modal */}
      <Dialog open={openNDCModalOpen} onOpenChange={setOpenNDCModalOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Open NDC Categories</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4">
            <div
              onClick={() => {
                setOpenNDCModalOpen(false);
                setModalData({ title: "Recovery Pending With Departments", data: mockNDCData.filter((r) => r.ndcStage === "Recovery Pending") });
                setModalOpen(true);
              }}
              className="cursor-pointer p-6 bg-card border border-border rounded-[4px] hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-foreground">Recovery Pending</span>
                <Building2 className="w-5 h-5 text-orange-600 flex-shrink-0" />
              </div>
              <p className="text-xs text-muted-foreground mb-2">(With Department)</p>
              <p className="text-2xl font-bold text-orange-600">{kpis.recoveryPending}</p>
            </div>
            <div
              onClick={() => {
                setOpenNDCModalOpen(false);
                setModalData({ title: "NDC Pending With GCC HR Approval", data: mockNDCData.filter((r) => r.ndcStage === "GCC Pending") });
                setModalOpen(true);
              }}
              className="cursor-pointer p-6 bg-card border border-border rounded-[4px] hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-foreground">NDC Pending With</span>
                <Clock className="w-5 h-5 text-blue-600 flex-shrink-0" />
              </div>
              <p className="text-xs text-muted-foreground mb-2">(GCC HR Approval)</p>
              <p className="text-2xl font-bold text-blue-600">{kpis.ndcPendingGCC}</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Closed NDC Modal */}
      <Dialog open={closedNDCModalOpen} onOpenChange={setClosedNDCModalOpen}>
        <DialogContent className="max-w-4xl sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Closed NDC Categories</DialogTitle>
          </DialogHeader>
          <div className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              {[
                { label: "F&F Closed", key: "Closed", count: kpis.closedFnfClosed, icon: CheckCircle, color: "text-teal-600", iconColor: "text-teal-600" },
                { label: "F&F Completed", key: "Done", count: kpis.closedFnfDone, icon: CheckCircle, color: "text-green-600", iconColor: "text-green-600" },
                { label: "F&F Open", key: "Open", count: kpis.closedFnfOpen, icon: FolderOpen, color: "text-blue-600", iconColor: "text-blue-600" },
                { label: "F&F Revision Required", key: "Revision Required", count: kpis.closedFnfRevision, icon: AlertCircle, color: "text-red-600", iconColor: "text-red-600" },
              ].map(({ label, key, count, icon: Icon, color, iconColor }) => (
                <div
                  key={key}
                  onClick={() => {
                    setClosedNDCModalOpen(false);
                    const closedCases = mockNDCData.filter((r) => r.ndcStage === "NDC Completed");
                    if (key === "Closed") {
                      setModalData({ title: label, data: closedCases.filter((r) => r.isFnfClosed) });
                    } else if (key === "Done") {
                      setModalData({ title: label, data: closedCases.filter((r) => r.isFnfCompleted) });
                    } else if (key === "Open") {
                      setModalData({ title: label, data: closedCases.filter((r) => !r.isFnfCompleted && !r.isFnfRevision) });
                    } else {
                      setModalData({ title: label, data: closedCases.filter((r) => r.isFnfRevision) });
                    }
                    setModalOpen(true);
                  }}
                  className="cursor-pointer p-5 bg-card border border-border rounded-[4px] hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3 gap-2">
                    <span className="text-sm font-semibold text-foreground leading-tight">{label}</span>
                    <Icon className={`w-5 h-5 flex-shrink-0 ${iconColor}`} />
                  </div>
                  <p className={`text-3xl font-bold ${color}`}>{count}</p>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>


      {/* Reminder Mail Dialog */}
      <Dialog open={reminderMailDialogOpen} onOpenChange={setReminderMailDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Send email</DialogTitle>
          </DialogHeader>
          <div className="p-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Email ID <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={reminderMailEmailTo}
                onChange={(e) => setReminderMailEmailTo(e.target.value)}
                placeholder="Enter email address"
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex gap-3">
              <button
                disabled={sendingReminder}
                onClick={async () => {
                  if (!reminderMailEmailTo) {
                    toast.error("Please enter an email address");
                    return;
                  }
                  setSendingReminder(true);
                  const toastId = toast.loading(`Sending reminder email to ${reminderMailEmailTo}...`);
                  try {
                    const res = await axios.post("/api/v1/send-delayed-reminder", {
                      email: reminderMailEmailTo,
                      type: reminderMailType,
                    });
                    const data = res.data?.data || res.data;
                    toast.dismiss(toastId);
                    toast.success(data?.message || "Reminder email sent successfully!");
                    setReminderMailDialogOpen(false);
                    setReminderMailEmailTo("");
                  } catch (err: any) {
                    toast.dismiss(toastId);
                    const detail = err?.response?.data?.detail || err?.message || "Failed to send email";
                    toast.error(`Email failed: ${detail}`);
                  } finally {
                    setSendingReminder(false);
                  }
                }}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
                {sendingReminder ? "Sending..." : "Send"}
              </button>
              <button
                onClick={() => {
                  setReminderMailDialogOpen(false);
                  setReminderMailEmailTo("");
                }}
                className="px-4 py-2 bg-muted text-foreground rounded-[4px] hover:bg-muted/80 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* NDC Delayed Table Modal */}
      <FullScreenModal
        open={ndcDelayedTableOpen}
        onClose={() => setNdcDelayedTableOpen(false)}
        title="NDC Delayed Cases"
        headerActions={
          <div className="flex items-center gap-3">
            <button
              disabled={mockNDCData.filter(isTopDelayed).length === 0}
              onClick={() => {
                setReminderMailEmailTo("");
                setReminderMailType("ndc_delayed");
                setReminderMailDialogOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Mail className="w-4 h-4" />
              Send Reminder
            </button>
            <button
              disabled={mockNDCData.filter(isTopDelayed).length === 0}
              onClick={() => {
                const allDelayed = mockNDCData.filter(isTopDelayed);
                const mappedData = allDelayed.map(r => ({
                  "Person Number": r.personNumber,
                  "Name": r.employeeName,
                  "Department": r.department,
                  "Last Working Date": r.lastWorkingDate,
                  "NDC Initiate Date": r.ndcInitiatedDate || "-",
                  "Pending With": getPendingDepartments(r),
                  "Days Delayed": getDelayedDays(r)
                }));
                exportToExcel(mappedData, "NDC_Delayed_Cases");
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export to Excel
            </button>
          </div>
        }
      >
        <div className="flex-1 overflow-auto p-6">
          {(() => {
            const allDelayed = mockNDCData.filter(isTopDelayed);
            const totalPages = Math.max(1, Math.ceil(allDelayed.length / itemsPerPage));
            const startIndex = (ndcDelayedCurrentPage - 1) * itemsPerPage;
            const sortedDelayed = [...allDelayed].sort((a, b) => getDelayedDays(b) - getDelayedDays(a));
            const paginatedDelayed = sortedDelayed.slice(startIndex, startIndex + itemsPerPage);

            return (
              <div className="h-full flex flex-col">
                <p className="text-sm text-muted-foreground mb-3 shrink-0">{allDelayed.length} delayed records</p>
                <div className="overflow-x-auto rounded-[4px] border border-border flex-1">
                  <table className="w-full text-sm">
                    <thead className="bg-muted sticky top-0 z-10">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Person Number</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Department</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Last Working Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">NDC Initiate Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Pending With</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Days Delayed</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border bg-card">
                      {allDelayed.length === 0 ? (
                        <tr><td colSpan={7} className="px-4 py-6 text-center text-muted-foreground">No delayed records found</td></tr>
                      ) : paginatedDelayed.map((record) => {
                        const days = getDelayedDays(record);
                        const badgeColor = days > 30
                          ? "bg-red-100 text-red-700"
                          : days >= 7
                            ? "bg-amber-100 text-amber-700"
                            : "bg-yellow-100 text-yellow-700";
                        return (
                          <tr key={record.id} className="hover:bg-muted/50">
                            <td className="px-4 py-3 whitespace-nowrap font-medium">{record.personNumber}</td>
                            <td className="px-4 py-3 whitespace-nowrap">{record.employeeName}</td>
                            <td className="px-4 py-3">{record.department}</td>
                            <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.lastWorkingDate)}</td>
                            <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.ndcInitiatedDate)}</td>
                            <td className="px-4 py-3 text-sm min-w-[220px] whitespace-normal" title={getPendingDepartments(record)}>
                              {getPendingDepartments(record)}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColor}`}>{days} days</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {allDelayed.length > 0 && (
                  <div className="mt-4 flex items-center justify-between shrink-0">
                    <div className="text-sm text-muted-foreground">
                      Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, allDelayed.length)} of {allDelayed.length} records
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setNdcDelayedCurrentPage(Math.max(1, ndcDelayedCurrentPage - 1))} disabled={ndcDelayedCurrentPage === 1} className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"><ChevronLeft className="w-4 h-4" /></button>
                      <span className="text-sm text-foreground">Page {ndcDelayedCurrentPage} of {totalPages}</span>
                      <button onClick={() => setNdcDelayedCurrentPage(Math.min(totalPages, ndcDelayedCurrentPage + 1))} disabled={ndcDelayedCurrentPage === totalPages} className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"><ChevronRight className="w-4 h-4" /></button>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </FullScreenModal>


      {/* In Progress Modal */}
      <FullScreenModal open={inProgressModalOpen} onClose={() => setInProgressModalOpen(false)} title="Pending NDC with departments">
        <FullScreenTable data={mockNDCData.filter((r) => r.ndcStage === "Recovery Pending")} title="Pending NDC with departments" />
      </FullScreenModal>

      {/* Pending Approval Modal */}
      <FullScreenModal open={pendingApprovalModalOpen} onClose={() => setPendingApprovalModalOpen(false)} title="Pending NDC with GCC">
        <FullScreenTable data={mockNDCData.filter((r) => r.ndcStage === "GCC Pending")} title="Pending NDC with GCC" />
      </FullScreenModal>

      {/* Overdue Modal */}
      <FullScreenModal open={overdueModalOpen} onClose={() => setOverdueModalOpen(false)} title="NDC Overdue after Exit">
        <FullScreenTable data={mockNDCData.filter(isOverdue)} title="NDC Overdue after Exit Cases" />
      </FullScreenModal>

      <FilterBar
        departmentFilter=""
        setDepartmentFilter={() => { }}
        ndcStageFilter={ndcStageFilter}
        setNdcStageFilter={setNdcStageFilter}
        approvalDepartmentFilter={approvalDepartmentFilter}
        setApprovalDepartmentFilter={setApprovalDepartmentFilter}
        approvalStatusFilter={approvalStatusFilter}
        setApprovalStatusFilter={setApprovalStatusFilter}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        departments={[]}
        ndcStages={ndcStages}
      />

      <div id="section-ndc-table">
        <NDCTable
          data={sortedData}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          itemsPerPage={itemsPerPage}
          onSort={handleSort}
          getRowHighlight={getRowHighlight}
          onDeleteRecord={handleDeleteRecord}
          onExport={(visibleColumns) => {
            const mappedData = sortedData.map(r => {
              const obj: any = {};
              visibleColumns.forEach(col => {
                let value = r[col.key as keyof NDCRecord];
                if (col.key === "pendingDepartments") {
                  value = getPendingDepartments(r);
                } else if (col.key.includes("ApprovalStatus")) {
                  if (value === "PENDING") value = "Pending";
                  else if (value === "IN_PROGRESS") value = "In Progress";
                  else if (value === "COMPLETED") value = "Completed";
                  else if (value === "NOT_APPLICABLE") value = "Not Applicable";
                  else if (value) value = value.toString().charAt(0).toUpperCase() + value.toString().slice(1).toLowerCase();
                  else value = "Not Applicable";
                }
                obj[col.label] = value;
              });
              return obj;
            });
            exportToExcel(mappedData, "NDC_Records");
          }}
        />
      </div>

      {/* Super Admin Delete Employee Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              Delete Employee Permanently
            </DialogTitle>
          </DialogHeader>
          <div className="p-4 space-y-4">
            <p className="text-sm text-foreground">
              Are you sure you want to permanently delete employee{" "}
              <span className="font-semibold text-red-600">{recordToDelete?.employeeName}</span>{" "}
              (Person Number: <span className="font-semibold">{recordToDelete?.personNumber}</span>)?
            </p>
            <p className="text-xs text-muted-foreground bg-red-50 dark:bg-red-950/40 p-2.5 rounded border border-red-200 dark:border-red-900/50">
              ⚠️ This will remove the employee from NDC tracking and <strong>permanently exclude</strong> them from all future automated SharePoint and manual Excel syncs.
            </p>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Reason for Deletion (Optional)
              </label>
              <input
                type="text"
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="e.g. Test record, exited before cutoff..."
                className="w-full px-3 py-2 text-sm border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-2 focus:ring-red-500"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                disabled={isDeleting}
                onClick={confirmDeleteRecord}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-[4px] hover:bg-red-700 transition-colors flex items-center justify-center gap-2 text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isDeleting ? "Deleting..." : "Permanently Delete"}
              </button>
              <button
                disabled={isDeleting}
                onClick={() => {
                  setDeleteConfirmOpen(false);
                  setRecordToDelete(null);
                }}
                className="px-4 py-2 bg-muted text-foreground rounded-[4px] hover:bg-muted/80 transition-colors text-sm font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
