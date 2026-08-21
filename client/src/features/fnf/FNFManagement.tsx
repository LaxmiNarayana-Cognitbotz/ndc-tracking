import { useState, useMemo, useEffect } from "react";
import axios from "../../lib/axios";
import { NDCRecord } from "../../types";
import { exportToExcel } from "../../utils/excelExport";
import { formatDate } from "../../utils/dateFormatter";
import { PPTDownloadButton } from "../../components/common/PPTDownloadButton";
import { FullScreenModal } from "../../components/common/FullScreenModal";
import { LoadingScreen } from "../../components/common/LoadingScreen";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { FileText, Download, Filter, CheckCircle, XCircle, Clock, Send, CheckSquare, Mail, TrendingUp, ChevronLeft, ChevronRight, AlertCircle } from "lucide-react";
import { toast } from "sonner";

export function FNFManagement() {
  const [mockNDCData, setMockNDCData] = useState<NDCRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    axios.get("/api/v1/fnf-records").then((res) => {
      const data = res.data?.data || res.data;
      setMockNDCData(Array.isArray(data) ? data : []);
      setIsLoading(false);
    });
  };


  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRecord, setSelectedRecord] = useState<NDCRecord | null>(null);
  const [actionDialogOpen, setActionDialogOpen] = useState(false);
  const [kpiModalOpen, setKpiModalOpen] = useState(false);
  const [kpiModalData, setKpiModalData] = useState<{ title: string; data: NDCRecord[] }>({ title: "", data: [] });
  const [mailDialogOpen, setMailDialogOpen] = useState(false);
  const [mailRecord, setMailRecord] = useState<NDCRecord | null>(null);
  const [mailEmailTo, setMailEmailTo] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [kpiCurrentPage, setKpiCurrentPage] = useState(1);
  const [reminderMailDialogOpen, setReminderMailDialogOpen] = useState(false);
  const [reminderMailEmailTo, setReminderMailEmailTo] = useState("");
  const [reminderMailType, setReminderMailType] = useState<string>("fnf_open");
  const [sendingReminder, setSendingReminder] = useState(false);
  const [sendingMail, setSendingMail] = useState(false);
  const [fnfDelayedTableOpen, setFnfDelayedTableOpen] = useState(false);
  const [fnfDelayedCurrentPage, setFnfDelayedCurrentPage] = useState(1);
  const [revisionComment, setRevisionComment] = useState("");
  const [showRevisionComment, setShowRevisionComment] = useState(false);

  // Reset to first page on filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, searchQuery]);

  // Helper to parse dates safely (handles YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY)
  const parseValidDate = (dateStr?: string): Date | null => {
    if (!dateStr || typeof dateStr !== "string" || !dateStr.trim()) return null;
    const str = dateStr.trim();
    const ddmmyyyyMatch = str.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
    if (ddmmyyyyMatch) {
      const day = parseInt(ddmmyyyyMatch[1], 10);
      const month = parseInt(ddmmyyyyMatch[2], 10) - 1;
      const year = parseInt(ddmmyyyyMatch[3], 10);
      const d = new Date(year, month, day);
      return isNaN(d.getTime()) ? null : d;
    }
    const d = new Date(str);
    return isNaN(d.getTime()) ? null : d;
  };

  // Helper to check case-insensitive status match
  const matchStatus = (val?: string, target?: string) =>
    (val || "").trim().toLowerCase() === (target || "").trim().toLowerCase();

  // Helper to get property in either camelCase or snake_case
  const getProp = (r: any, camelKey: string, snakeKey: string) =>
    r[camelKey] !== undefined ? r[camelKey] : r[snakeKey];

  // F&F eligible = NDC Completed AND GCC HR Completed (or F&F completed/closed)
  const isEligible = (r: NDCRecord) => {
    const stage = getProp(r, "ndcStage", "ndc_stage");
    const gccStatus = getProp(r, "gccHrApprovalStatus", "gcc_hr_approval_status");
    const isCompleted = getProp(r, "isFnfCompleted", "is_fnf_completed");
    const isClosed = getProp(r, "isFnfClosed", "is_fnf_closed");

    const isNdcDone = matchStatus(stage, "NDC Completed") || matchStatus(stage, "Completed");
    const isGccDone = matchStatus(gccStatus, "Completed");
    return (isNdcDone && isGccDone) || !!isCompleted || !!isClosed;
  };

  const eligibleRecords = useMemo(() => mockNDCData.filter(isEligible), [mockNDCData]);

  const filteredData = useMemo(() => {
    let filtered = eligibleRecords;
    if (statusFilter) {
      if (statusFilter === "Done") filtered = filtered.filter((r) => getProp(r, "isFnfCompleted", "is_fnf_completed") && !getProp(r, "isFnfClosed", "is_fnf_closed"));
      else if (statusFilter === "Closed") filtered = filtered.filter((r) => getProp(r, "isFnfClosed", "is_fnf_closed"));
      else if (statusFilter === "Open") filtered = filtered.filter((r) => !getProp(r, "isFnfCompleted", "is_fnf_completed") && !getProp(r, "isFnfClosed", "is_fnf_closed") && !getProp(r, "isFnfRevision", "is_fnf_revision"));
      else if (statusFilter === "Revision Required") filtered = filtered.filter((r) => getProp(r, "isFnfRevision", "is_fnf_revision"));
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          String(getProp(r, "employeeName", "employee_name") || "").toLowerCase().includes(query) ||
          String(getProp(r, "personNumber", "person_number") || "").toLowerCase().includes(query)
      );
    }
    return filtered;
  }, [eligibleRecords, statusFilter, searchQuery]);

  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [kpiItemsPerPage, setKpiItemsPerPage] = useState(20);
  const totalPages = Math.max(1, Math.ceil(filteredData.length / itemsPerPage));
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = filteredData.slice(startIndex, startIndex + itemsPerPage);

  const kpiTotalPages = Math.max(1, Math.ceil(kpiModalData.data.length / kpiItemsPerPage));
  const kpiStartIndex = (kpiCurrentPage - 1) * kpiItemsPerPage;
  const kpiPaginatedData = kpiModalData.data.slice(kpiStartIndex, kpiStartIndex + kpiItemsPerPage);



  // F&F Delayed: NDC Completed but F&F not completed, past LWD
  const fnfDelayedData = useMemo(() => {
    return mockNDCData.filter((r) => {
      const stage = getProp(r, "ndcStage", "ndc_stage");
      const isCompleted = getProp(r, "isFnfCompleted", "is_fnf_completed");
      const lwd = getProp(r, "lastWorkingDate", "last_working_date");
      if (!matchStatus(stage, "NDC Completed") || isCompleted) return false;
      const parsedLwd = parseValidDate(lwd);
      if (!parsedLwd) return false;
      const days = Math.ceil((new Date().getTime() - parsedLwd.getTime()) / (1000 * 60 * 60 * 24));
      return days > 0;
    });
  }, [mockNDCData]);

  // F&F TAT calculation: measures days from GCC Initiate Date to F&F completion.
  // Start date priority: gccInitiateDate -> ndcCompletedDate -> lastWorkingDate
  // End date fallback: fnfCompletedDate -> fnfRevisionCompletedDate -> fnfActionDate
  const tatRecordsWithDays = useMemo(() => {
    return eligibleRecords.map((r) => {
      const isCompleted = getProp(r, "isFnfCompleted", "is_fnf_completed");
      const isClosed = getProp(r, "isFnfClosed", "is_fnf_closed");
      const fnfStatus = getProp(r, "fnfStatus", "fnf_status");

      const isDone = !!isCompleted || !!isClosed || matchStatus(fnfStatus, "Done") || matchStatus(fnfStatus, "Completed");
      if (!isDone) return null;

      const gccInitiate = getProp(r, "gccInitiateDate", "gcc_initiate_date");
      const ndcCompleted = getProp(r, "ndcCompletedDate", "ndc_completed_date");
      const lwd = getProp(r, "lastWorkingDate", "last_working_date");

      const fnfCompleted = getProp(r, "fnfCompletedDate", "fnf_completed_date");
      const fnfRevCompleted = getProp(r, "fnfRevisionCompletedDate", "fnf_revision_completed_date");
      const fnfAction = getProp(r, "fnfActionDate", "fnf_action_date");

      // F&F TAT = days from GCC Initiate Date to F&F completion
      const startDate = parseValidDate(gccInitiate) || parseValidDate(ndcCompleted) || parseValidDate(lwd);
      const endDate = parseValidDate(fnfCompleted) || parseValidDate(fnfRevCompleted) || parseValidDate(fnfAction);

      if (!startDate || !endDate) return null;

      const diffMs = Math.abs(endDate.getTime() - startDate.getTime());
      const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
      return { record: r, days };
    }).filter((item): item is { record: NDCRecord; days: number } => item !== null);
  }, [eligibleRecords]);

  const tatRecords = useMemo(() => tatRecordsWithDays.map((item) => item.record), [tatRecordsWithDays]);

  // F&F TAT w.r.t Last Working Date: measures days from LWD to F&F completion.
  const tatRecordsWithDaysLWD = useMemo(() => {
    return eligibleRecords.map((r) => {
      const isCompleted = getProp(r, "isFnfCompleted", "is_fnf_completed");
      const isClosed = getProp(r, "isFnfClosed", "is_fnf_closed");
      const fnfStatus = getProp(r, "fnfStatus", "fnf_status");

      const isDone = !!isCompleted || !!isClosed || matchStatus(fnfStatus, "Done") || matchStatus(fnfStatus, "Completed");
      if (!isDone) return null;

      const lwd = getProp(r, "lastWorkingDate", "last_working_date");
      const fnfCompleted = getProp(r, "fnfCompletedDate", "fnf_completed_date");
      const fnfRevCompleted = getProp(r, "fnfRevisionCompletedDate", "fnf_revision_completed_date");

      const startDate = parseValidDate(lwd);
      const endDate = parseValidDate(fnfCompleted) || parseValidDate(fnfRevCompleted);

      if (!startDate || !endDate) return null;

      const diffMs = Math.abs(endDate.getTime() - startDate.getTime());
      const days = Math.round(diffMs / (1000 * 60 * 60 * 24));
      return { record: r, days };
    }).filter((item): item is { record: NDCRecord; days: number } => item !== null);
  }, [eligibleRecords]);

  const tatRecordsLWD = useMemo(() => tatRecordsWithDaysLWD.map((item) => item.record), [tatRecordsWithDaysLWD]);

  const fnfStats = useMemo(() => {
    const total = eligibleRecords.length;
    const done = eligibleRecords.filter((r) => getProp(r, "isFnfCompleted", "is_fnf_completed") || getProp(r, "isFnfClosed", "is_fnf_closed")).length;
    const open = eligibleRecords.filter((r) => !getProp(r, "isFnfCompleted", "is_fnf_completed") && !getProp(r, "isFnfClosed", "is_fnf_closed") && !getProp(r, "isFnfRevision", "is_fnf_revision")).length;
    const revision = eligibleRecords.filter((r) => getProp(r, "isFnfRevision", "is_fnf_revision")).length;
    const closed = eligibleRecords.filter((r) => getProp(r, "isFnfClosed", "is_fnf_closed")).length;

    const avgTAT = tatRecordsWithDays.length > 0
      ? Math.round(tatRecordsWithDays.reduce((sum, item) => sum + item.days, 0) / tatRecordsWithDays.length)
      : 0;

    const avgTATLWD = tatRecordsWithDaysLWD.length > 0
      ? Math.round(tatRecordsWithDaysLWD.reduce((sum, item) => sum + item.days, 0) / tatRecordsWithDaysLWD.length)
      : 0;

    return { total, done, open, revision, closed, avgTAT, avgTATLWD };
  }, [eligibleRecords, tatRecordsWithDays, tatRecordsWithDaysLWD]);

  const handleAction = (record: NDCRecord, action: "closed" | "revision") => {
    if (action === "closed") {
      // Mark as F&F Closed (which automatically completes it too)
      axios.put(`/api/v1/ndc-records/${record.id}`, {
        is_fnf_closed: true,
        is_fnf_completed: true,
        fnf_document_count: 1,
      }).then(() => {
        fetchData();
        toast.success(`F&F marked as Closed and Completed for ${record.employeeName} (${record.personNumber})`);
      });
    } else {
      // Mark as Revision Required (multiple docs) — include comment
      axios.put(`/api/v1/ndc-records/${record.id}`, {
        is_fnf_revision: true,
        is_fnf_closed: false,
        is_fnf_completed: false,
        fnf_document_count: 2,
        fnf_revision_comment: revisionComment.trim() || undefined,
      }).then(() => {
        fetchData();
        toast.success(`F&F marked as Revision Required for ${record.employeeName} (${record.personNumber})`);
      });
    }
    setActionDialogOpen(false);
    setSelectedRecord(null);
    setRevisionComment("");
    setShowRevisionComment(false);
  };

  const handleDocumentView = (record: NDCRecord) => {
    toast.success(`Downloading document for ${record.employeeName}...`);
    
    // Use native browser download. By updating location.href, the browser handles
    // the redirect and downloads the file silently without opening a new tab.
    const baseUrl = import.meta.env.BASE_URL?.replace(/\/$/, '') || '';
    window.location.href = `${baseUrl}/api/ff/download/${record.personNumber}`;
  };

  const handleKPIClick = (type: "total" | "done" | "open" | "revision" | "closed" | "avgTAT" | "avgTATLWD" | "fnfDelayed") => {
    const map = {
      total: { title: "Total F&F In Process", data: eligibleRecords },
      done: { title: "F&F Completed", data: eligibleRecords.filter((r) => r.isFnfCompleted || r.isFnfClosed) },
      open: { title: "F&F Open", data: eligibleRecords.filter((r) => !r.isFnfCompleted && !r.isFnfClosed && !r.isFnfRevision) },
      revision: { title: "Revision Required", data: eligibleRecords.filter((r) => r.isFnfRevision) },
      closed: { title: "F&F Closed", data: eligibleRecords.filter((r) => r.isFnfClosed) },
      avgTAT: { title: "F&F TAT w.r.t NDC Closure Date", data: tatRecords },
      avgTATLWD: { title: "F&F TAT w.r.t Last Working Date", data: tatRecordsLWD },
      fnfDelayed: { title: "F&F Delayed Cases", data: fnfDelayedData },
    };
    setKpiModalData(map[type]);
    setKpiCurrentPage(1);
    setKpiModalOpen(true);
  };

  const getFNFStatusLabel = (record: NDCRecord) => {
    if (record.isFnfClosed) return "Closed";
    if (record.isFnfCompleted) return "Completed";
    if (record.isFnfRevision) return "Revision Required";
    return "Open";
  };

  const getFNFStatusBadge = (record: NDCRecord) => {
    const label = getFNFStatusLabel(record);
    const colorMap: Record<string, string> = {
      "Closed": "bg-teal-50 text-teal-700 border-teal-200",
      "Completed": "bg-green-50 text-green-700 border-green-200",
      "Open": "bg-blue-50 text-blue-700 border-blue-200",
      "Revision Required": "bg-red-50 text-red-700 border-red-200",
    };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-[4px] text-xs font-medium border ${colorMap[label] || ""}`}>
        {label}
      </span>
    );
  };

  const getNDCStatusBadge = (record: NDCRecord) => {
    const stage = record.ndcStage || "Recovery Pending";
    const displayLabel = stage === "NDC Completed" ? "Completed" : stage;
    const colorMap: Record<string, string> = {
      "NDC Completed": "bg-green-50 text-green-700 border-green-200",
      "GCC Pending": "bg-orange-50 text-orange-700 border-orange-200",
      "Recovery Pending": "bg-blue-50 text-blue-700 border-blue-200",
    };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-[4px] text-xs font-medium border ${colorMap[stage] || "bg-gray-50 text-gray-700 border-gray-200"}`}>
        {displayLabel}
      </span>
    );
  };

  const kpiCards = [
    { type: "total" as const, label: "Total F&F In Process", value: fnfStats.total, icon: FileText, color: "text-primary" },
    { type: "done" as const, label: "F&F Completed", value: fnfStats.done, icon: CheckCircle, color: "text-green-600" },
    { type: "closed" as const, label: "F&F Closed", value: fnfStats.closed, icon: CheckCircle, color: "text-teal-600" },
    { type: "open" as const, label: "F&F Open", value: fnfStats.open, icon: Clock, color: "text-blue-600" },
    { type: "revision" as const, label: "Revision Required", value: fnfStats.revision, icon: XCircle, color: "text-red-600" },
    { type: "fnfDelayed" as const, label: "F&F Delayed Cases", value: fnfDelayedData.length, icon: AlertCircle, color: "text-orange-600" },
    { type: "avgTAT" as const, label: "F&F TAT w.r.t NDC Closure Date (In Days)", value: fnfStats.avgTAT, icon: TrendingUp, color: "text-purple-600" },
    { type: "avgTATLWD" as const, label: "F&F TAT w.r.t Last Working Date (In Days)", value: fnfStats.avgTATLWD, icon: TrendingUp, color: "text-indigo-600" },
  ];

  const [fnfDelayedItemsPerPage, setFnfDelayedItemsPerPage] = useState(20);
  const fnfDelayedTotalPages = Math.max(1, Math.ceil(fnfDelayedData.length / fnfDelayedItemsPerPage));
  const fnfDelayedStartIndex = (fnfDelayedCurrentPage - 1) * fnfDelayedItemsPerPage;
  const fnfDelayedPaginated = fnfDelayedData.slice(fnfDelayedStartIndex, fnfDelayedStartIndex + fnfDelayedItemsPerPage);

  if (isLoading) return <LoadingScreen />;

  const handleDownloadPPT = async () => {
    const { createPPT, addImageSlide } = await import("../../utils/pptExport");
    const pptx = createPPT("FnF Management Dashboard");

    await addImageSlide(pptx, "F&F KPI Summary", "section-fnf-kpis");

    await pptx.writeFile({ fileName: "FnF_Management_Dashboard.pptx" });
  };



  return (
    <div className="p-8 space-y-6 bg-background min-h-full">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">F&amp;F Document Management</h1>
          <p className="text-muted-foreground mt-2">Full &amp; Final Settlement Processing</p>
        </div>
        <PPTDownloadButton onDownload={handleDownloadPPT} />
      </div>



      {/* KPI Cards */}
      <div id="section-fnf-kpis" className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {kpiCards.map(({ type, label, value, icon: Icon, color }) => {
          const isInteractive = type !== "avgTAT" && type !== "fnfDelayed";
          const handleClick = type === "fnfDelayed"
            ? () => { setFnfDelayedTableOpen(true); setFnfDelayedCurrentPage(1); }
            : isInteractive ? () => handleKPIClick(type) : undefined;
          return (
            <div
              key={type}
              onClick={handleClick}
              className={`bg-card rounded-[4px] p-5 border border-border h-[110px] flex flex-col justify-between ${type !== "avgTAT" ? "cursor-pointer hover:scale-105 transition-transform duration-200" : ""
                }`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-sm text-muted-foreground leading-tight">{label}</span>
                <Icon className={`w-5 h-5 flex-shrink-0 ${color}`} />
              </div>
              <p className={`text-3xl font-bold ${color}`}>{value}</p>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="bg-card rounded-[4px] p-6 border border-border">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Filter className="w-5 h-5" />
          Filters
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">F&amp;F Status Filter</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All statuses</option>
              <option value="Closed">Closed</option>
              <option value="Done">Completed</option>
              <option value="Open">Open</option>
              <option value="Revision Required">Revision Required</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">Search Employee / Name</label>
            <input
              type="text"
              placeholder="Name or person number"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
      </div>

      {/* F&F Records Table */}
      <div id="section-fnf-table" className="bg-card rounded-[4px] border border-border overflow-hidden">
        <div className="p-6 border-b border-border flex items-center justify-between">
          <h2 className="text-xl font-bold">F&amp;F Records Table</h2>
          <div className="flex items-center gap-3">
            {(statusFilter === "Open" || statusFilter === "Revision Required") && (
              <button
                disabled={filteredData.length === 0}
                onClick={() => {
                  const type = statusFilter === "Open" ? "fnf_open" : "fnf_revision";
                  setReminderMailType(type);
                  setReminderMailEmailTo("");
                  setReminderMailDialogOpen(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Mail className="w-4 h-4" />
                Send Reminder
              </button>
            )}
            <button
              disabled={filteredData.length === 0}
              onClick={() => {
                const mappedData = filteredData.map(r => ({
                  "Person number": r.personNumber,
                  "Employee name": r.employeeName,
                  "Department": r.department,
                  "Last working date": formatDate(r.lastWorkingDate),
                  "NDC Final Cleared Date": formatDate(r.ndcCompletedDate),
                  "F&F status": getFNFStatusLabel(r),
                  "NDC status": r.ndcStage === "NDC Completed" ? "Completed" : (r.ndcStage || "Recovery Pending"),
                  "F&F completed date": formatDate(r.fnfCompletedDate),
                }));
                exportToExcel(mappedData, "FNF_Records");
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export to Excel
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Person number</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Employee name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Department</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Last working date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC Final Cleared Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">F&amp;F status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">F&amp;F completed date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {paginatedData.map((record) => (
                <tr key={record.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3 text-sm font-medium">{record.personNumber}</td>
                  <td className="px-4 py-3 text-sm">{record.employeeName}</td>
                  <td className="px-4 py-3 text-sm">{record.department}</td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.lastWorkingDate)}</td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.ndcCompletedDate)}</td>
                  <td className="px-4 py-3 text-sm">{getFNFStatusBadge(record)}</td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">{formatDate(record.fnfCompletedDate)}</td>
                  <td className="px-4 py-3 text-sm">{getNDCStatusBadge(record)}</td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex gap-2 items-center">
                      <button
                        onClick={() => handleDocumentView(record)}
                        disabled={record.fnfDocumentCount === 0}
                        className={`p-2 rounded-[4px] transition-colors ${record.fnfDocumentCount === 0
                            ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                            : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
                          }`}
                        title={record.fnfDocumentCount === 0 ? "No document found" : "View document"}
                      >
                        <FileText className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setSelectedRecord(record); setActionDialogOpen(true); }}
                        className="p-2 rounded-[4px] bg-green-50 text-green-600 hover:bg-green-100 transition-colors"
                        title="Confirm F&F status"
                      >
                        <CheckSquare className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setMailRecord(record); setMailEmailTo(""); setMailDialogOpen(true); }}
                        disabled={record.fnfDocumentCount === 0}
                        className={`p-2 rounded-[4px] transition-colors ${record.fnfDocumentCount === 0
                            ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                            : 'bg-primary text-primary-foreground hover:bg-primary/90'
                          }`}
                        title={record.fnfDocumentCount === 0 ? "No document found to send" : "Send email"}
                      >
                        <Mail className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredData.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-muted-foreground">No F&amp;F records found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {filteredData.length > 0 && (
          <div className="px-6 py-4 border-t border-border flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="text-sm text-muted-foreground">
                Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredData.length)} of{" "}
                {filteredData.length} records
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
        )}
      </div>

      {/* KPI Full-Screen Modal */}
      <FullScreenModal
        open={kpiModalOpen}
        onClose={() => setKpiModalOpen(false)}
        title={kpiModalData.title}
        headerActions={
          <div className="flex items-center gap-3">
            {(kpiModalData.title === "F&F Open" || kpiModalData.title === "Revision Required") && (
              <button
                disabled={kpiModalData.data.length === 0}
                onClick={() => {
                  const type = kpiModalData.title === "F&F Open" ? "fnf_open" : "fnf_revision";
                  setReminderMailType(type);
                  setReminderMailEmailTo("");
                  setReminderMailDialogOpen(true);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Mail className="w-4 h-4" />
                Send Reminder
              </button>
            )}
            <button
              disabled={kpiModalData.data.length === 0}
              onClick={() => {
                const mappedData = kpiModalData.data.map(r => ({
                  "Person number": r.personNumber,
                  "Name": r.employeeName,
                  "Department": r.department,
                  "Last working date": formatDate(r.lastWorkingDate),
                  "NDC Final Cleared Date": formatDate(r.ndcCompletedDate),
                  "NDC stage": r.ndcStage,
                  "F&F status": getFNFStatusLabel(r),
                  "F&F completed date": formatDate(r.fnfCompletedDate)
                }));
                exportToExcel(mappedData, kpiModalData.title || "KPI_Records");
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              Export to Excel
            </button>
          </div>
        }
      >
        <div className="flex flex-col flex-1 overflow-hidden p-4">
          <div className="bg-card rounded-[4px] border border-border flex flex-col flex-1 overflow-hidden">
            <div className="p-3 border-b border-border bg-muted/50 shrink-0">
              <span className="text-sm font-semibold text-foreground">
                Detailed records ({kpiModalData.data.length} records)
              </span>
            </div>
            <div className="overflow-x-auto overflow-y-auto flex-1">
              <table className="w-full text-sm">
                <thead className="bg-muted sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Person number</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Department</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Last working date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC Final Cleared Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">NDC stage</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">F&amp;F status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">F&amp;F completed date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-card">
                  {kpiPaginatedData.map((record) => (
                    <tr key={record.id} className="hover:bg-muted/50">
                      <td className="px-4 py-3 whitespace-nowrap">{record.personNumber}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{record.employeeName}</td>
                      <td className="px-4 py-3">{record.department}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.lastWorkingDate)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.ndcCompletedDate)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{record.ndcStage}</td>
                      <td className="px-4 py-3">{getFNFStatusBadge(record)}</td>
                      <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.fnfCompletedDate)}</td>
                    </tr>
                  ))}
                  {kpiModalData.data.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">No records found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {kpiModalData.data.length > 0 && (
              <div className="px-6 py-4 border-t border-border flex flex-wrap items-center justify-between gap-4 bg-card">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {kpiStartIndex + 1} to {Math.min(kpiStartIndex + kpiItemsPerPage, kpiModalData.data.length)} of{" "}
                    {kpiModalData.data.length} records
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Rows per page:</span>
                    <select
                      value={kpiItemsPerPage}
                      onChange={(e) => {
                        setKpiItemsPerPage(Number(e.target.value));
                        setKpiCurrentPage(1);
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
                    onClick={() => setKpiCurrentPage(Math.max(1, kpiCurrentPage - 1))}
                    disabled={kpiCurrentPage === 1}
                    className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-foreground">
                    Page {kpiCurrentPage} of {kpiTotalPages}
                  </span>
                  <button
                    onClick={() => setKpiCurrentPage(Math.min(kpiTotalPages, kpiCurrentPage + 1))}
                    disabled={kpiCurrentPage === kpiTotalPages}
                    className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </FullScreenModal>

      {/* Confirmation Dialog */}
      <Dialog open={actionDialogOpen} onOpenChange={(open) => { setActionDialogOpen(open); if (!open) { setShowRevisionComment(false); setRevisionComment(""); } }}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-foreground">{showRevisionComment ? "Revision Comment" : "F&amp;F document confirmation"}</DialogTitle>
          </DialogHeader>
          {selectedRecord && (
            <div className="space-y-6 pt-4">
              <div className="bg-[#f8fafc] border border-slate-200 p-5 rounded-[6px] space-y-1.5">
                <p className="text-sm text-slate-600">
                  Employee: <span className="font-semibold text-slate-900">{selectedRecord.employeeName}</span>
                </p>
                <p className="text-sm text-slate-500">
                  Person number: <span className="text-slate-700">{selectedRecord.personNumber}</span>
                </p>
                <p className="text-sm text-slate-500">
                  Department: <span className="text-slate-700">{selectedRecord.department}</span>
                </p>
              </div>

              {!showRevisionComment ? (
                <>
                  <p className="text-base text-slate-900">
                    Is the F&amp;F document ready to be processed?
                  </p>

                  <div className="flex gap-4">
                    <button
                      onClick={() => handleAction(selectedRecord, "closed")}
                      className="flex-1 px-4 py-3 bg-[#00a651] text-white rounded-[6px] hover:bg-[#008f45] transition-colors flex items-center justify-center gap-2 font-semibold text-sm shadow-sm"
                    >
                      <CheckCircle className="w-5 h-5 shrink-0" />
                      Closed
                    </button>
                    <button
                      onClick={() => { setShowRevisionComment(true); setRevisionComment(""); }}
                      className="flex-1 px-4 py-3 bg-[#e30613] text-white rounded-[6px] hover:bg-[#c2050f] transition-colors flex items-center justify-center gap-2 font-semibold text-sm shadow-sm"
                    >
                      <XCircle className="w-5 h-5 shrink-0" />
                      Needs revision
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-slate-700">
                      Reason for revision <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      value={revisionComment}
                      onChange={(e) => setRevisionComment(e.target.value.slice(0, 1000))}
                      placeholder="Enter reason for revision (e.g., Missing salary slip, Form 16 not attached...)"
                      rows={4}
                      className="w-full px-3 py-2.5 border border-slate-300 rounded-[6px] text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                    />
                    <p className="text-xs text-slate-400 text-right">{revisionComment.length}/1000</p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => { setShowRevisionComment(false); setRevisionComment(""); }}
                      className="flex-1 px-4 py-2.5 border border-slate-300 text-slate-700 rounded-[6px] hover:bg-slate-50 transition-colors text-sm font-medium"
                    >
                      Back
                    </button>
                    <button
                      onClick={() => handleAction(selectedRecord, "revision")}
                      disabled={!revisionComment.trim()}
                      className="flex-1 px-4 py-2.5 bg-[#e30613] text-white rounded-[6px] hover:bg-[#c2050f] transition-colors text-sm font-semibold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      <XCircle className="w-4 h-4 shrink-0" />
                      Submit Revision
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Mail Dialog */}
      <Dialog open={mailDialogOpen} onOpenChange={setMailDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Send email</DialogTitle>
          </DialogHeader>
          <div className="p-4 space-y-4">
            {mailRecord && (
              <p className="text-sm text-muted-foreground">
                <strong>Employee Name:</strong> <span className="font-medium text-foreground">{mailRecord.employeeName}</span>
              </p>
            )}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Email ID <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={mailEmailTo}
                onChange={(e) => setMailEmailTo(e.target.value)}
                placeholder="Enter email address"
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="flex gap-3">
              <button
                disabled={sendingMail}
                onClick={() => {
                  if (!mailRecord) return;
                  if (!mailEmailTo) {
                    toast.error("Please enter an email address");
                    return;
                  }
                  setSendingMail(true);
                  const toastId = toast.loading(`Sending F&F details email to ${mailEmailTo}...`);
                  axios.post("/api/v1/send-fnf-email", {
                    email: mailEmailTo,
                    record_id: parseInt(mailRecord.id)
                  })
                    .then(() => {
                      toast.dismiss(toastId);
                      toast.success(`Email sent successfully to ${mailEmailTo}`);
                      setMailDialogOpen(false);
                      setMailRecord(null);
                      setMailEmailTo("");
                    })
                    .catch((err) => {
                      toast.dismiss(toastId);
                      const errMsg = err.response?.data?.detail || err.message || "Failed to send email";
                      toast.error(errMsg);
                    })
                    .finally(() => {
                      setSendingMail(false);
                    });
                }}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-[4px] hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
                {sendingMail ? "Sending..." : "Send"}
              </button>
              <button
                onClick={() => { setMailDialogOpen(false); setMailRecord(null); setMailEmailTo(""); }}
                className="px-4 py-2 bg-muted text-foreground rounded-[4px] hover:bg-muted/80 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reminder Mail Dialog */}
      <Dialog open={reminderMailDialogOpen} onOpenChange={setReminderMailDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Send Reminder Email</DialogTitle>
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

      {/* F&F Delayed Table Modal */}
      <FullScreenModal
        open={fnfDelayedTableOpen}
        onClose={() => setFnfDelayedTableOpen(false)}
        title="F&F Delayed Cases"
        headerActions={
          <div className="flex items-center gap-3">
            <button
              disabled={fnfDelayedData.length === 0}
              onClick={() => {
                setReminderMailEmailTo("");
                setReminderMailType("fnf_delayed");
                setReminderMailDialogOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Mail className="w-4 h-4" />
              Send Reminder
            </button>
            <button
              disabled={fnfDelayedData.length === 0}
              onClick={() => {
                const mappedData = fnfDelayedData.map(r => ({
                  "Person Number": r.personNumber,
                  "Name": r.employeeName,
                  "Department": r.department,
                  "Last Working Date": formatDate(r.lastWorkingDate),
                  "NDC Initiate Date": formatDate(r.ndcInitiatedDate),
                  "NDC Final Cleared Date": formatDate(r.ndcCompletedDate || r.gccHrApprovalDate),
                  "F&F Status": r.fnfStatus,
                  "Days Delayed": Math.ceil((new Date().getTime() - new Date(r.lastWorkingDate).getTime()) / (1000 * 60 * 60 * 24))
                }));
                exportToExcel(mappedData, "FnF_Delayed_Cases");
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
          <div className="h-full flex flex-col">
            <h3 className="text-base font-semibold text-orange-800 mb-3 shrink-0">
              F&amp;F delayed cases <span className="ml-2 text-sm font-normal text-muted-foreground">({fnfDelayedData.length} records)</span>
            </h3>
            <div className="overflow-x-auto rounded-[4px] border border-orange-200 flex-1">
              <table className="w-full text-sm">
                <thead className="bg-orange-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Person Number</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Department</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Last Working Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">NDC Initiate Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">NDC Final Cleared Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">F&amp;F Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">Days Delayed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-orange-100 bg-card">
                  {fnfDelayedData.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-6 text-center text-muted-foreground">No records found</td></tr>
                  ) : fnfDelayedPaginated.map((record) => {
                    const delayDays = Math.ceil((new Date().getTime() - new Date(record.lastWorkingDate).getTime()) / (1000 * 60 * 60 * 24));
                    return (
                      <tr key={record.id} className="hover:bg-orange-50/50">
                        <td className="px-4 py-3 whitespace-nowrap font-medium">{record.personNumber}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{record.employeeName}</td>
                        <td className="px-4 py-3">{record.department}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.lastWorkingDate)}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.ndcInitiatedDate)}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{formatDate(record.ndcCompletedDate || record.gccHrApprovalDate)}</td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center px-2 py-1 rounded-[4px] text-xs font-medium bg-orange-100 text-orange-700 whitespace-nowrap">{record.fnfStatus}</span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">{delayDays} days</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {fnfDelayedData.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-4 shrink-0">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {fnfDelayedStartIndex + 1} to {Math.min(fnfDelayedStartIndex + fnfDelayedItemsPerPage, fnfDelayedData.length)} of {fnfDelayedData.length} records
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Rows per page:</span>
                    <select
                      value={fnfDelayedItemsPerPage}
                      onChange={(e) => {
                        setFnfDelayedItemsPerPage(Number(e.target.value));
                        setFnfDelayedCurrentPage(1);
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
                  <button onClick={() => setFnfDelayedCurrentPage(Math.max(1, fnfDelayedCurrentPage - 1))} disabled={fnfDelayedCurrentPage === 1} className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"><ChevronLeft className="w-4 h-4" /></button>
                  <span className="text-sm text-foreground">Page {fnfDelayedCurrentPage} of {fnfDelayedTotalPages}</span>
                  <button onClick={() => setFnfDelayedCurrentPage(Math.min(fnfDelayedTotalPages, fnfDelayedCurrentPage + 1))} disabled={fnfDelayedCurrentPage === fnfDelayedTotalPages} className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"><ChevronRight className="w-4 h-4" /></button>
                </div>
              </div>
            )}
          </div>
        </div>
      </FullScreenModal>
    </div>
  );
}
