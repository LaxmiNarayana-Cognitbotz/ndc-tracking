import { useMemo, useState, useEffect } from "react";
import axios from "../../lib/axios";
import { NDCRecord } from "../../types";
import { PPTDownloadButton } from "../../components/common/PPTDownloadButton";
import { LoadingScreen } from "../../components/common/LoadingScreen";
import { exportToExcel } from "../../utils/excelExport";
import { Download } from "lucide-react";

import HighchartsReact from "highcharts-react-official";
import Highcharts from "highcharts";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import { format, parseISO } from "date-fns";

const DEPT_STATUS_FIELDS: Record<string, keyof NDCRecord> = {
  "RM": "rmApprovalStatus",
  "IT": "itApprovalStatus",
  "Abex": "abexApprovalStatus",
  "Telecom": "telecomApprovalStatus",
  "Store": "storeApprovalStatus",
  "Safety": "safetyApprovalStatus",
  "Administration": "administrationApprovalStatus",
  "Security": "securityApprovalStatus",
  "HR": "hrApprovalStatus",
  "GCC HR": "gccHrApprovalStatus",
  "Business Specific": "businessSpecificApprovalStatus",
  "Final Abex": "finalAbexApprovalStatus",
  "Legatrix": "legatrixApprovalStatus",
};

const DEPT_DATE_FIELDS: Record<string, keyof NDCRecord> = {
  "RM": "rmApprovalDate",
  "IT": "itApprovalDate",
  "Abex": "abexApprovalDate",
  "Telecom": "telecomApprovalDate",
  "Store": "storeApprovalDate",
  "Safety": "safetyApprovalDate",
  "Administration": "administrationApprovalDate",
  "Security": "securityApprovalDate",
  "HR": "hrApprovalDate",
  "GCC HR": "gccHrApprovalDate",
  "Business Specific": "businessSpecificApprovalDate",
  "Final Abex": "finalAbexApprovalDate",
  "Legatrix": "legatrixApprovalDate",
};

const APPROVAL_DEPT_OPTIONS = Object.keys(DEPT_STATUS_FIELDS).sort((a, b) => a.localeCompare(b));

const getFnfCompletionDays = (record: NDCRecord) => {
  let completedDateStr = record.fnfCompletedDate || record.ndcCompletedDate;
  if (!completedDateStr) {
    const approvalDates = Object.keys(record)
      .filter((k) => k.endsWith("ApprovalDate") && (record as any)[k])
      .map((k) => (record as any)[k]);
    if (approvalDates.length > 0) {
      completedDateStr = approvalDates.sort().reverse()[0];
    } else {
      completedDateStr = record.ndcInitiatedDate || record.lastWorkingDate;
    }
  }
  if (!completedDateStr || !record.lastWorkingDate) return null;
  const completed = new Date(completedDateStr);
  const lastWorking = new Date(record.lastWorkingDate);
  return Math.ceil((completed.getTime() - lastWorking.getTime()) / (1000 * 60 * 60 * 24));
};

const getNdcCompletionDays = (record: NDCRecord) => {
  let completedDateStr = record.ndcCompletedDate;
  if (!completedDateStr) {
    const approvalDates = Object.keys(record)
      .filter((k) => k.endsWith("ApprovalDate") && (record as any)[k])
      .map((k) => (record as any)[k]);
    if (approvalDates.length > 0) {
      completedDateStr = approvalDates.sort().reverse()[0];
    } else {
      completedDateStr = record.ndcInitiatedDate || record.lastWorkingDate;
    }
  }
  if (!completedDateStr || !record.ndcInitiatedDate) return null;
  const completed = new Date(completedDateStr);
  const initiated = new Date(record.ndcInitiatedDate);
  return Math.max(0, Math.ceil((completed.getTime() - initiated.getTime()) / (1000 * 60 * 60 * 24)));
};

const getFnfRevisionDays = (record: NDCRecord) => {
  if (!record.fnfRevisionStartDate) return null;
  const completedDateStr = record.fnfRevisionCompletedDate || new Date().toISOString().split('T')[0];
  const completed = new Date(completedDateStr);
  const start = new Date(record.fnfRevisionStartDate);
  return Math.max(0, Math.ceil((completed.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
};

export function Analytics() {
  const [mockNDCData, setMockNDCData] = useState<NDCRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    axios.get("/api/v1/analytics-records").then((res) => {
      const data = res.data?.data || res.data;
      setMockNDCData(Array.isArray(data) ? data : []);
      setIsLoading(false);
    });
  }, []);

  const [bottleneckApprovalFilter, setBottleneckApprovalFilter] = useState("");
  const [ndcChartApprovalFilter, setNdcChartApprovalFilter] = useState("");
  const [topDelayedFilter, setTopDelayedFilter] = useState<"All" | "NDC" | "F&F">("All");


  // NDC Status data for Highcharts Pie + Bar
  const ndcChartFilteredData = useMemo(() => {
    if (!ndcChartApprovalFilter) return mockNDCData;
    const field = DEPT_STATUS_FIELDS[ndcChartApprovalFilter];
    return field ? mockNDCData.filter((r) => r[field] !== "" && r[field] !== "Not Applicable") : mockNDCData;
  }, [mockNDCData, ndcChartApprovalFilter]);

  const statusData = useMemo(() => {
    const completed = mockNDCData.filter((r) => r.ndcStage === "NDC Completed").length;
    const pending = mockNDCData.filter((r) => r.ndcStage === "GCC Pending").length;
    const inProgress = mockNDCData.filter((r) => r.ndcStage === "Recovery Pending").length;
    return [
      { name: "Completed", y: completed, color: "#10b981" },
      { name: "Pending", y: pending, color: "#ef4444" },
      { name: "In Progress", y: inProgress, color: "#f59e0b" },
    ].filter((d) => d.y > 0);
  }, [mockNDCData]);

  const totalStatusCount = statusData.reduce((sum, d) => sum + d.y, 0);

  const highchartsPieOptions: Highcharts.Options = useMemo(() => ({
    chart: { type: "pie", height: 280, backgroundColor: "transparent", margin: [10, 10, 10, 10], animation: { duration: 800 } },
    title: { text: "" },
    credits: { enabled: false },
    tooltip: { pointFormat: "<b>{point.y}</b> ({point.percentage:.1f}%)" },
    accessibility: { enabled: false },
    legend: { enabled: false },
    plotOptions: {
      pie: {
        innerSize: "75%",
        size: "85%",
 showInLegend: false,
        dataLabels: {
          enabled: true,
          format: "{point.name}: {point.y} ({point.percentage:.1f}%)",
          style: { fontSize: "12px", fontWeight: "bold" },
          distance: 14,
        },
      },
    },
    series: [{
      type: "pie",
      name: "NDC Status",
      data: statusData,
    }],
  }), [statusData]);

  // F&F Status Breakdown (moved from FNF Management)
  const fnfStatusBreakdownData = useMemo(() => {
    const activeRecords = mockNDCData.filter(r => r.fnfStatus && r.fnfStatus.trim() !== "");
    const total = activeRecords.length;
    const closed = activeRecords.filter((r) => r.fnfStatus === "Closed").length;
    const done = activeRecords.filter((r) => r.fnfStatus === "Done" || r.fnfStatus === "Completed").length;
    const open = activeRecords.filter((r) => r.fnfStatus === "Open").length;
    const revision = activeRecords.filter((r) => r.fnfStatus === "Revision Required").length;
    const notStarted = total - closed - done - open - revision;
    const entries = [
      { name: "Closed", y: closed, color: "#0d9488" },
      { name: "Completed", y: done, color: "#10b981" },
      { name: "Open", y: open, color: "#3b82f6" },
      { name: "Revision Required", y: revision, color: "#ef4444" },
      { name: "Not started", y: notStarted, color: "#6b7280" },
    ].filter((d) => d.y > 0);
    return { entries, total };
  }, [mockNDCData]);

  const fnfStatusPieOptions: Highcharts.Options = useMemo(() => ({
    chart: { type: "pie", height: 280, backgroundColor: "transparent", margin: [10, 10, 10, 10], animation: { duration: 800 } },
    title: { text: "" },
    credits: { enabled: false },
    tooltip: { pointFormat: "<b>{point.y}</b> ({point.percentage:.1f}%)" },
    accessibility: { enabled: false },
    legend: { enabled: false },
    plotOptions: {
      pie: {
        innerSize: "75%",
        size: "85%",
        showInLegend: false,
        dataLabels: {
          enabled: true,
          format: "{point.name}: {point.y} ({point.percentage:.1f}%)",
          style: { fontSize: "12px", fontWeight: "bold" },
          distance: 14,
        },
      },
    },
    series: [{
      type: "pie",
      name: "F&F Status",
      data: fnfStatusBreakdownData.entries,
    }],
  }), [fnfStatusBreakdownData]);

  // F&F Analysis
  const fnfAnalysisData = useMemo(() => {
    const cats = {
      "On or due date": 0,
      "Within 2 days": 0,
      "3–7 days": 0,
      "7–30 days": 0,
      "More than 30 days": 0,
    };

    const activeRecords = mockNDCData.filter(
      (r) =>
        r.isFnfCompleted ||
        r.isFnfClosed ||
        (r.fnfStatus &&
          (r.fnfStatus === "Closed" ||
            r.fnfStatus === "Done" ||
            r.fnfStatus === "Completed"))
    );
    activeRecords.forEach((record) => {
      const days = getFnfCompletionDays(record);
      if (days !== null) {
        if (days <= 0) cats["On or due date"]++;
        else if (days <= 2) cats["Within 2 days"]++;
        else if (days <= 7) cats["3–7 days"]++;
        else if (days <= 30) cats["7–30 days"]++;
        else cats["More than 30 days"]++;
      }
    });

    const total = Object.values(cats).reduce((a, b) => a + b, 0);
    const colorMap: Record<string, string> = {
      "On or due date": "#10b981",
      "Within 2 days": "#f97316",
      "3–7 days": "#f59e0b",
      "7–30 days": "#ef4444",
      "More than 30 days": "#b91c1c",
    };

    return Object.entries(cats).map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? Math.round((count / total) * 100) : 0,
      fill: colorMap[name],
    }));
  }, [mockNDCData]);

  // NDC Analysis (filtered by Approval Department — shows dept-specific delay)
  const ndcAnalysisData = useMemo(() => {
    const cats = {
      "On or due date": 0,
      "Within 2 days": 0,
      "3–7 days": 0,
      "7–30 days": 0,
      "More than 30 days": 0,
    };

    ndcChartFilteredData.forEach((record) => {
      if (record.ndcStage !== "NDC Completed") return;

      let days: number | null = null;

      if (ndcChartApprovalFilter) {
        // Department-specific: days from ndcInitiatedDate to that dept's approval date
        const dateField = DEPT_DATE_FIELDS[ndcChartApprovalFilter];
        const statusField = DEPT_STATUS_FIELDS[ndcChartApprovalFilter];
        if (!dateField || !statusField) return;
        if (record[statusField] !== "Completed") return;
        const deptDateStr = record[dateField] as string;
        if (!deptDateStr || !record.ndcInitiatedDate) return;
        const deptDate = new Date(deptDateStr);
        const initiated = new Date(record.ndcInitiatedDate);
        days = Math.max(0, Math.ceil((deptDate.getTime() - initiated.getTime()) / (1000 * 60 * 60 * 24)));
      } else {
        // All: overall NDC completion days
        days = getNdcCompletionDays(record);
      }

      if (days === null) return;

      if (days <= 0) cats["On or due date"]++;
      else if (days <= 2) cats["Within 2 days"]++;
      else if (days <= 7) cats["3–7 days"]++;
      else if (days <= 30) cats["7–30 days"]++;
      else cats["More than 30 days"]++;
    });

    const total = Object.values(cats).reduce((a, b) => a + b, 0);
    const colorMap: Record<string, string> = {
      "On or due date": "#10b981",
      "Within 2 days": "#f97316",
      "3–7 days": "#f59e0b",
      "7–30 days": "#ef4444",
      "More than 30 days": "#b91c1c",
    };

    return Object.entries(cats).map(([name, count]) => ({
      name,
      count,
      pct: total > 0 ? Math.round((count / total) * 100) : 0,
      fill: colorMap[name],
    }));
  }, [ndcChartFilteredData, ndcChartApprovalFilter]);

  // F&F Closed TAT Analysis
  const fnfClosedTATData = useMemo(() => {
    const cats: Record<string, { count: number; color: string }> = {
      "Within 7 Days": { count: 0, color: "#10b981" },
      "Within 15 Days": { count: 0, color: "#f97316" },
      "Within 30 Days": { count: 0, color: "#f59e0b" },
      "More than 30 Days": { count: 0, color: "#ef4444" },
    };

    const activeRecords = mockNDCData.filter(
      (r) =>
        r.isFnfCompleted ||
        r.isFnfClosed ||
        (r.fnfStatus &&
          (r.fnfStatus === "Closed" ||
            r.fnfStatus === "Done" ||
            r.fnfStatus === "Completed"))
    );
    activeRecords.forEach((record) => {
      const days = getFnfCompletionDays(record);
      if (days === null) return;
      if (days <= 7) cats["Within 7 Days"].count++;
      else if (days <= 15) cats["Within 15 Days"].count++;
      else if (days <= 30) cats["Within 30 Days"].count++;
      else cats["More than 30 Days"].count++;
    });

    return Object.entries(cats).map(([name, { count, color }]) => ({ name, count, color }));
  }, [mockNDCData]);

  // F&F Revision TAT Analysis
  const fnfRevisionTATData = useMemo(() => {
    const cats: Record<string, { count: number; color: string }> = {
      "On or due date": { count: 0, color: "#10b981" },
      "Within 2 days": { count: 0, color: "#84cc16" },
      "3–7 days": { count: 0, color: "#f59e0b" },
      "7–30 days": { count: 0, color: "#f97316" },
      "More than 30 day": { count: 0, color: "#ef4444" },
    };

    mockNDCData.forEach((record) => {
      const days = getFnfRevisionDays(record);
      if (days === null) return;
      if (days <= 0) cats["On or due date"].count++;
      else if (days <= 2) cats["Within 2 days"].count++;
      else if (days <= 7) cats["3–7 days"].count++;
      else if (days <= 30) cats["7–30 days"].count++;
      else cats["More than 30 day"].count++;
    });

    const total = Object.values(cats).reduce((sum, item) => sum + item.count, 0);
    return Object.entries(cats).map(([name, { count, color }]) => ({
      name,
      count,
      pct: total > 0 ? Math.round((count / total) * 100) : 0,
      color,
      fill: color,
    }));
  }, [mockNDCData]);

  // NDC Closed TAT Analysis (previously named fnfClosedTATData)
  const ndcClosedTATData = useMemo(() => {
    const cats: Record<string, { count: number; color: string }> = {
      "Within 7 Days": { count: 0, color: "#10b981" },
      "Within 15 Days": { count: 0, color: "#f97316" },
      "Within 30 Days": { count: 0, color: "#f59e0b" },
      "More than 30 Days": { count: 0, color: "#ef4444" },
    };

    mockNDCData.forEach((record) => {
      if (record.ndcStage !== "NDC Completed") return;
      const days = getNdcCompletionDays(record);
      if (days === null) return;
      if (days <= 7) cats["Within 7 Days"].count++;
      else if (days <= 15) cats["Within 15 Days"].count++;
      else if (days <= 30) cats["Within 30 Days"].count++;
      else cats["More than 30 Days"].count++;
    });

    return Object.entries(cats).map(([name, { count, color }]) => ({ name, count, color }));
  }, [mockNDCData]);

  // Approval Bottleneck
  const bottleneckFilteredData = useMemo(() => {
    if (!bottleneckApprovalFilter) return mockNDCData;
    const field = DEPT_STATUS_FIELDS[bottleneckApprovalFilter];
    return field ? mockNDCData.filter((r) => r[field] !== "" && r[field] !== "Not Applicable") : mockNDCData;
  }, [mockNDCData, bottleneckApprovalFilter]);

  const approvalBottleneckData = useMemo(() => {
    let result = APPROVAL_DEPT_OPTIONS.map((name) => {
      const field = DEPT_STATUS_FIELDS[name];
      const completed = bottleneckFilteredData.filter((r) => r[field] === "Completed").length;
      const pending = bottleneckFilteredData.filter((r) => r[field] === "Pending").length;
      
      const totalActive = completed + pending;
      const completedPct = totalActive > 0 ? Math.round((completed / totalActive) * 100) : 0;
      const pendingPct = totalActive > 0 ? 100 - completedPct : 0;

      return {
        name,
        pending,
        completed,
        totalActive,
        completedPct,
        pendingPct,
      };
    }).filter((item) => item.totalActive > 0); // Exclude departments with no active (completed or pending) cases

    if (bottleneckApprovalFilter) result = result.filter((i) => i.name === bottleneckApprovalFilter);
    return result;
  }, [bottleneckFilteredData, bottleneckApprovalFilter]);

  // Monthly Trend
  const monthlyTrendData = useMemo(() => {
    const monthCounts: Record<string, { initiated: number; completed: number }> = {};
    mockNDCData.forEach((record) => {
      if (record.ndcInitiatedDate) {
        const month = record.ndcInitiatedDate.substring(0, 7);
        if (!monthCounts[month]) monthCounts[month] = { initiated: 0, completed: 0 };
        monthCounts[month].initiated++;
      }
      if (record.ndcCompletedDate) {
        const month = record.ndcCompletedDate.substring(0, 7);
        if (!monthCounts[month]) monthCounts[month] = { initiated: 0, completed: 0 };
        monthCounts[month].completed++;
      }
    });

    return Object.entries(monthCounts)
      .sort()
      .map(([month, data]) => ({
        month,
        displayMonth: (() => {
          try { return format(parseISO(month + "-01"), "MMM yyyy"); } catch { return month; }
        })(),
        initiated: data.initiated,
        completed: data.completed,
      }));
  }, [mockNDCData]);

  const totalMonthly = monthlyTrendData.reduce((s, d) => s + d.initiated + d.completed, 0);

  // Top Delayed Cases
  const allDelayedCases = useMemo(() => {
    const ndcDelayed = mockNDCData
      .filter((r) => r.ndcStage !== "NDC Completed")
      .map((r) => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const lwd = new Date(r.lastWorkingDate);
        lwd.setHours(0, 0, 0, 0);
        const days = Math.max(0, Math.ceil((today.getTime() - lwd.getTime()) / (1000 * 60 * 60 * 24)));
        return { ...r, delayDays: days, category: "NDC Pending" as const };
      })
      .filter((r) => r.delayDays > 0);

    const fnfDelayed = mockNDCData
      .filter((r) => r.fnfStatus && r.fnfStatus !== "Done" && r.fnfStatus !== "Completed")
      .map((r) => {
        const days = Math.max(0, Math.ceil((new Date().getTime() - new Date(r.lastWorkingDate).getTime()) / (1000 * 60 * 60 * 24)));
        return { ...r, delayDays: days, category: "F&F Pending" as const };
      })
      .filter((r) => r.delayDays > 0);

    return [...ndcDelayed, ...fnfDelayed].sort((a, b) => b.delayDays - a.delayDays);
  }, [mockNDCData]);

  const topDelayedCases = useMemo(() => {
    if (topDelayedFilter === "NDC") return allDelayedCases.filter((r) => r.category === "NDC Pending").slice(0, 10);
    if (topDelayedFilter === "F&F") return allDelayedCases.filter((r) => r.category === "F&F Pending").slice(0, 10);
    return allDelayedCases.slice(0, 10);
  }, [allDelayedCases, topDelayedFilter]);

  const renderInitiatedLabel = (props: any) => {
    const { x, y, value, index } = props;
    if (value === undefined || value === null || value <= 0) return <g />;

    const pct = Math.round((value / (totalMonthly || 1)) * 100);
    if (pct <= 0) return <g />;

    const currentPoint = monthlyTrendData[index];
    if (!currentPoint) return <g />;

    const initiatedVal = currentPoint.initiated || 0;
    const completedVal = currentPoint.completed || 0;

    let dy = -10;
    const diff = Math.abs(initiatedVal - completedVal);

    if (initiatedVal > 0 && completedVal > 0 && diff <= 12) {
      if (initiatedVal > completedVal) {
        dy = completedVal <= 8 ? -26 : -14;
      } else if (completedVal > initiatedVal) {
        dy = initiatedVal <= 8 ? -10 : 14;
      } else {
        dy = -26;
      }
    } else {
      const position = initiatedVal >= completedVal ? "top" : "bottom";
      dy = (position === "bottom" && initiatedVal <= 8) || position === "top" ? -10 : 14;
    }

    return (
      <text x={x} y={y} dy={dy} fill="#1e5a8e" textAnchor="middle" fontSize={12} fontWeight="bold">
        {pct}%
      </text>
    );
  };

  const renderCompletedLabel = (props: any) => {
    const { x, y, value, index } = props;
    if (value === undefined || value === null || value <= 0) return <g />;

    const pct = Math.round((value / (totalMonthly || 1)) * 100);
    if (pct <= 0) return <g />;

    const currentPoint = monthlyTrendData[index];
    if (!currentPoint) return <g />;

    const initiatedVal = currentPoint.initiated || 0;
    const completedVal = currentPoint.completed || 0;

    let dy = -10;
    const diff = Math.abs(initiatedVal - completedVal);

    if (initiatedVal > 0 && completedVal > 0 && diff <= 12) {
      if (completedVal > initiatedVal) {
        dy = initiatedVal <= 8 ? -26 : -14;
      } else if (initiatedVal > completedVal) {
        dy = completedVal <= 8 ? -10 : 14;
      } else {
        dy = -10;
      }
    } else {
      const position = completedVal >= initiatedVal ? "top" : "bottom";
      dy = (position === "bottom" && completedVal <= 8) || position === "top" ? -10 : 14;
    }

    return (
      <text x={x} y={y} dy={dy} fill="#10b981" textAnchor="middle" fontSize={12} fontWeight="bold">
        {pct}%
      </text>
    );
  };

  const makeCustomBarLabel = (data: { count: number; pct: number }[]) => {
    return ({ x, y, width, index }: any) => {
      const entry = data[index];
      if (!entry || !entry.count) return null;
      return (
        <text x={Number(x) + Number(width) / 2} y={Number(y) - 8} fill="#374151" textAnchor="middle" fontSize={12} fontWeight="bold">
          {entry.count} ({entry.pct}%)
        </text>
      );
    };
  };

  const analyticsSections = [
    { id: "section-ndc-overview", title: "NDC Status Overview" },
    { id: "section-fnf-overview", title: "F&F Status Overview" },
    { id: "section-bottleneck-combined", title: "NDC Approval Status & F&F Revision TAT Analysis" },
    { id: "section-monthly", title: "Monthly Trend NDC Clearance" },
    { id: "section-fnf-tat", title: "F&F Closed TAT Analysis" },
    { id: "section-ndc-tat", title: "NDC Closed TAT Analysis" },
    { id: "section-delayed", title: "Top Delayed Cases" },
  ];

  if (isLoading) return <LoadingScreen />;

  const handleDownloadPPT = async () => {
    const { createPPT, addImageSlide } = await import("../../utils/pptExport");
    const pptx = createPPT("Analytics Dashboard");
    
    for (const section of analyticsSections) {
      if (section.id === "section-delayed") continue; // Commented out for future as per user request
      await addImageSlide(pptx, section.title, section.id);
    }
    
    await pptx.writeFile({ fileName: "Analytics_Dashboard.pptx" });
  };

  return (
    <div className="p-8 space-y-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Analytics Dashboard</h1>
          <p className="text-muted-foreground mt-2">Insights &amp; Performance Metrics</p>
        </div>
        <PPTDownloadButton onDownload={handleDownloadPPT} />
      </div>

      {/* NDC Status Overview — Pie 50% left + NDC Analysis bar 50% right */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-ndc-overview">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">NDC Status Overview</h3>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-foreground">Approval department:</label>
            <select
              value={ndcChartApprovalFilter}
              onChange={(e) => setNdcChartApprovalFilter(e.target.value)}
              className="px-3 py-1.5 border border-border rounded-[4px] bg-input-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All</option>
              {APPROVAL_DEPT_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-6">
          {/* Pie 50% */}
          <div className="flex flex-col">
            <h4 className="text-sm font-semibold text-muted-foreground mb-2 text-center">NDC Status Pie</h4>
            <div className="relative">
              <HighchartsReact highcharts={Highcharts} options={highchartsPieOptions} />
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider text-center whitespace-nowrap mb-0.5">
                  Total Employee Exit
                </span>
                <span className="text-2xl font-bold text-gray-900 leading-none">{totalStatusCount}</span>
              </div>
            </div>
            {/* Pie legend */}
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2">
              {statusData.map((item) => (
                <span key={item.name} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
                  {item.name}
                </span>
              ))}
            </div>
          </div>
          {/* Bar 50% */}
          <div className="flex flex-col">
            <h4 className="text-sm font-semibold text-muted-foreground mb-2 text-center">NDC Analysis</h4>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={ndcAnalysisData} margin={{ top: 28, right: 20, left: 5, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} interval={0} angle={-35} textAnchor="end" height={70} />
                <YAxis stroke="#64748b" label={{ value: "Number of Exited Employees", angle: -90, position: "insideLeft", offset: 15, style: { fontSize: 10, textAnchor: "middle" } }} allowDecimals={false} />
                <Tooltip formatter={(val: number) => [val, "Count"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={55} minPointSize={4} isAnimationActive={true} animationDuration={900}>
                  {ndcAnalysisData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  <LabelList content={makeCustomBarLabel(ndcAnalysisData)} dataKey="count" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {/* Bar legend */}
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2">
              {[
                { label: "On or due date", color: "#10b981" },
                { label: "Within 2 days", color: "#f97316" },
                { label: "3–7 days", color: "#f59e0b" },
                { label: "7–30 days", color: "#ef4444" },
                { label: "More than 30 days", color: "#b91c1c" },
              ].map((item) => (
                <span key={item.label} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* F&F Status Breakdown 50% left + F&F Analysis bar 50% right */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-fnf-overview">
        <h3 className="text-lg font-bold mb-4">F&amp;F Status Overview</h3>
        <div className="grid grid-cols-2 gap-6">
          {/* F&F Status Pie 50% */}
          <div className="flex flex-col">
            <h4 className="text-sm font-semibold text-muted-foreground mb-2 text-center">F&amp;F Status Breakdown Pie</h4>
            <div className="relative">
              <HighchartsReact highcharts={Highcharts} options={fnfStatusPieOptions} />
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider text-center whitespace-nowrap mb-0.5">
                  Total F&amp;F In Process
                </span>
                <span className="text-2xl font-bold text-gray-900 leading-none">{fnfStatusBreakdownData.total}</span>
              </div>
            </div>
            {/* Pie legend */}
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2">
              {fnfStatusBreakdownData.entries.map((item) => (
                <span key={item.name} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
                  {item.name}
                </span>
              ))}
            </div>
          </div>
          {/* F&F Analysis Bar 50% */}
          <div className="flex flex-col">
            <h4 className="text-sm font-semibold text-muted-foreground mb-2 text-center">F&amp;F Analysis</h4>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={fnfAnalysisData} margin={{ top: 28, right: 20, left: 5, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} interval={0} angle={-35} textAnchor="end" height={70} />
                <YAxis stroke="#64748b" label={{ value: "Number of Exited Employees", angle: -90, position: "insideLeft", offset: 15, style: { fontSize: 10, textAnchor: "middle" } }} allowDecimals={false} />
                <Tooltip formatter={(val: number) => [val, "Count"]} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={55} minPointSize={4} isAnimationActive={true} animationDuration={900}>
                  {fnfAnalysisData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  <LabelList content={makeCustomBarLabel(fnfAnalysisData)} dataKey="count" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {/* Bar legend */}
            <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 pt-2">
              {[
                { label: "On or due date", color: "#10b981" },
                { label: "Within 2 days", color: "#f97316" },
                { label: "3–7 days", color: "#f59e0b" },
                { label: "7–30 days", color: "#ef4444" },
                { label: "More than 30 days", color: "#b91c1c" },
              ].map((item) => (
                <span key={item.label} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: item.color }} />
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Approval NDC Analysis & F&F Revision TAT Analysis side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" id="section-bottleneck-combined">
        {/* NDC Approval Status by Department — Horizontal Stacked Bar Chart with Outside Labels */}
        <div className="bg-card rounded-[4px] p-6 border border-border" id="section-bottleneck">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 mb-4">
            <h3 className="text-lg font-bold whitespace-nowrap">NDC Approval Status by Department</h3>
            <div className="flex items-center gap-2 ml-auto">
              <label className="text-sm font-medium text-foreground">Approval:</label>
              <select
                value={bottleneckApprovalFilter}
                onChange={(e) => setBottleneckApprovalFilter(e.target.value)}
                className="px-3 py-1.5 border border-border rounded-[4px] bg-input-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">All approvals</option>
                {APPROVAL_DEPT_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={420}>
            <BarChart
              data={approvalBottleneckData}
              margin={{ top: 25, right: 10, left: -15, bottom: 40 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fontSize: 10 }}
                interval={0}
                angle={-35}
                textAnchor="end"
                height={70}
                label={{ value: "Approval Department", position: "insideBottom", offset: -5, style: { fontSize: 11, fill: "#64748b" } }}
              />
              <YAxis
                stroke="#64748b"
                allowDecimals={false}
                tick={{ fontSize: 10 }}
                domain={[0, "dataMax + 40"]}
              />
              <Tooltip formatter={(val: number) => [val, "Cases"]} />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="completed" fill="#10b981" name="Completed" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={true} animationDuration={800}>
                <LabelList 
                  position="top" 
                  offset={6} 
                  style={{ fill: "#374151", fontSize: 10, fontWeight: "bold" }} 
                  valueAccessor={(entry: any) => {
                    const payload = entry?.payload ?? entry;
                    const val = payload.completed ?? 0;
                    const pct = payload.completedPct ?? 0;
                    return val > 0 ? `${val} (${pct}%)` : "";
                  }}
                />
              </Bar>
              <Bar dataKey="pending" fill="#ef4444" name="Pending" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={true} animationDuration={800} animationBegin={200}>
                <LabelList 
                  position="top" 
                  offset={6} 
                  style={{ fill: "#374151", fontSize: 10, fontWeight: "bold" }} 
                  valueAccessor={(entry: any) => {
                    const payload = entry?.payload ?? entry;
                    const val = payload.pending ?? 0;
                    const pct = payload.pendingPct ?? 0;
                    return val > 0 ? `${val} (${pct}%)` : "";
                  }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* F&F Revision TAT Analysis */}
        <div className="bg-card rounded-[4px] p-6 border border-border" id="section-fnf-revision-tat">
          <div className="mb-4">
            <h3 className="text-lg font-bold">F&amp;F Revision TAT Analysis</h3>
            {/* <p className="text-xs text-muted-foreground mt-1">
              Tracks Turnaround Time (TAT) from when a record is marked as <strong>Revision Required</strong> until it is marked as <strong>Completed/Closed</strong>. For active/open revisions, the TAT is calculated up to today.
            </p> */}
          </div>
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={fnfRevisionTATData} margin={{ top: 28, right: 20, left: 5, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-35}
                textAnchor="end"
                height={70}
                label={{ value: "TAT Category", position: "insideBottom", offset: -5, style: { fontSize: 12, fill: "#64748b" } }}
              />
              <YAxis
                stroke="#64748b"
                allowDecimals={false}
                label={{ value: "Number of Employees", angle: -90, position: "insideLeft", offset: 15, style: { fontSize: 12, fill: "#64748b", textAnchor: "middle" } }}
              />
              <Tooltip formatter={(val: number) => [val, "Count"]} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={55} minPointSize={4} isAnimationActive={true} animationDuration={900}>
                {fnfRevisionTATData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                <LabelList content={makeCustomBarLabel(fnfRevisionTATData)} dataKey="count" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 pt-2">
            {[
              { label: "On or due date", color: "#10b981" },
              { label: "Within 2 days", color: "#84cc16" },
              { label: "3–7 days", color: "#f59e0b" },
              { label: "7–30 days", color: "#f97316" },
              { label: "More than 30 day", color: "#ef4444" },
            ].map((item) => (
              <span key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>


      {/* Monthly Trend */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-monthly">
        <h3 className="text-lg font-bold mb-4">Monthly Trend NDC Clearance</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={monthlyTrendData} margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="displayMonth" stroke="#64748b" />
            <YAxis
              stroke="#64748b"
              allowDecimals={false}
              label={{ value: "Number of Cases", angle: -90, position: "insideLeft", offset: -5, style: { fontSize: 12, fill: "#64748b", textAnchor: "middle" } }}
            />
            <Tooltip labelFormatter={(label) => label} />
            <Legend />
            <Line type="monotone" dataKey="initiated" stroke="#1e5a8e" name="NDC initiated" strokeWidth={3} dot={{ r: 4 }} isAnimationActive={true} animationDuration={1000} label={renderInitiatedLabel} />
            <Line type="monotone" dataKey="completed" stroke="#10b981" name="NDC completed" strokeWidth={3} dot={{ r: 4 }} isAnimationActive={true} animationDuration={1000} animationBegin={300} label={renderCompletedLabel} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* F&F Closed TAT Analysis */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-fnf-tat">
        <h3 className="text-lg font-bold mb-4">F&amp;F Closed TAT Analysis</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={fnfClosedTATData} margin={{ top: 20, right: 40, left: 20, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="name"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              interval={0}
              label={{ value: "TAT Category", position: "insideBottom", offset: -20, style: { fontSize: 12, fill: "#64748b" } }}
            />
            <YAxis
              stroke="#64748b"
              allowDecimals={false}
              label={{ value: "Number of Employees", angle: -90, position: "insideLeft", offset: 10, style: { fontSize: 12, fill: "#64748b", textAnchor: "middle" } }}
            />
            <Tooltip formatter={(val: number) => [val, "Employees"]} />
            <Line
              type="monotone"
              dataKey="count"
              name="Employees"
              strokeWidth={3}
              isAnimationActive={true}
              animationDuration={1000}
              dot={(props: any) => {
                const { cx, cy, index } = props;
                const color = fnfClosedTATData[index]?.color || "#1e5a8e";
                return <circle key={index} cx={cx} cy={cy} r={6} fill={color} stroke="white" strokeWidth={2} />;
              }}
              stroke="#1e5a8e"
              label={{ position: "top", offset: 14, fontSize: 13, fontWeight: "bold", fill: "#374151", formatter: (v: number) => v > 0 ? v : "" }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 pt-2">
          {[
            { label: "Within 7 Days", color: "#10b981" },
            { label: "Within 15 Days", color: "#f97316" },
            { label: "Within 30 Days", color: "#f59e0b" },
            { label: "More than 30 Days", color: "#ef4444" },
          ].map((item) => (
            <span key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      </div>

      {/* NDC Closed TAT Analysis */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-ndc-tat">
        <h3 className="text-lg font-bold mb-4">NDC Closed TAT Analysis</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={ndcClosedTATData} margin={{ top: 20, right: 40, left: 20, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="name"
              stroke="#64748b"
              tick={{ fontSize: 11 }}
              interval={0}
              label={{ value: "TAT Category", position: "insideBottom", offset: -20, style: { fontSize: 12, fill: "#64748b" } }}
            />
            <YAxis
              stroke="#64748b"
              allowDecimals={false}
              label={{ value: "Number of Employees", angle: -90, position: "insideLeft", offset: 10, style: { fontSize: 12, fill: "#64748b", textAnchor: "middle" } }}
            />
            <Tooltip formatter={(val: number) => [val, "Employees"]} />
            <Line
              type="monotone"
              dataKey="count"
              name="Employees"
              strokeWidth={3}
              isAnimationActive={true}
              animationDuration={1000}
              dot={(props: any) => {
                const { cx, cy, index } = props;
                const color = ndcClosedTATData[index]?.color || "#1e5a8e";
                return <circle key={index} cx={cx} cy={cy} r={6} fill={color} stroke="white" strokeWidth={2} />;
              }}
              stroke="#1e5a8e"
              label={{ position: "top", offset: 14, fontSize: 13, fontWeight: "bold", fill: "#374151", formatter: (v: number) => v > 0 ? v : "" }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 pt-2">
          {[
            { label: "Within 7 Days", color: "#10b981" },
            { label: "Within 15 Days", color: "#f97316" },
            { label: "Within 30 Days", color: "#f59e0b" },
            { label: "More than 30 Days", color: "#ef4444" },
          ].map((item) => (
            <span key={item.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      </div>



      {/* Top Delayed Cases Charts (Original F&F, Revision F&F) */}
      <div className="bg-card rounded-[4px] p-6 border border-border" id="section-delayed">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">Top Delayed Cases (F&amp;F Pending, NDC Pending Cases)</h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-muted rounded-[4px] p-1">
              {(["All", "NDC", "F&F"] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => setTopDelayedFilter(opt)}
                  className={`px-3 py-1.5 rounded-[4px] text-sm font-medium transition-colors ${
                    topDelayedFilter === opt
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
            <button
              onClick={() => {
                const mappedData = topDelayedCases.map(r => ({
                  "Person Number": r.personNumber,
                  "Employee Name": r.employeeName,
                  "Department": r.department,
                  "Last Working Date": r.lastWorkingDate,
                  "Category": r.category,
                  "Delay (Days)": r.delayDays
                }));
                exportToExcel(mappedData, `Top_Delayed_Cases_${topDelayedFilter.replace("&", "n")}`);
              }}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-sm rounded-[4px] hover:bg-primary/90 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Person Number</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Employee Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Department</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Last Working Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Category</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">Delay (Days)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {topDelayedCases.map((record, i) => (
                <tr key={`${record.id}-${i}`} className="hover:bg-muted/50">
                  <td className="px-4 py-3 text-sm font-medium">{record.personNumber}</td>
                  <td className="px-4 py-3 text-sm">{record.employeeName}</td>
                  <td className="px-4 py-3 text-sm">{record.department}</td>
                  <td className="px-4 py-3 text-sm">{record.lastWorkingDate}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
                      record.category === "NDC Pending"
                        ? "bg-blue-50 text-blue-700 border border-blue-200"
                        : "bg-orange-50 text-orange-700 border border-orange-200"
                    }`}>
                      {record.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap bg-red-50 text-red-700 border border-red-200">
                      {record.delayDays} days
                    </span>
                  </td>
                </tr>
              ))}
              {topDelayedCases.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">No delayed cases found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
