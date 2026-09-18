import PptxGenJS from "pptxgenjs";
import { formatDate } from "./dateFormatter";

export interface AnalyticsEditableData {
  statusData: { name: string; y: number; color: string }[];
  ndcAnalysisData: { name: string; count: number; pct: number; fill: string }[];
  fnfStatusBreakdownData: { entries: { name: string; y: number; color: string }[]; total: number };
  fnfAnalysisData: { name: string; count: number; pct: number; fill: string }[];
  approvalBottleneckData: {
    name: string;
    pending: number;
    completed: number;
    totalActive: number;
    completedPct: number;
    pendingPct: number;
  }[];
  fnfRevisionTATData: { name: string; count: number; pct: number; color: string; fill: string }[];
  monthlyTrendData: { month: string; displayMonth: string; initiated: number; completed: number }[];
  fnfClosedTATData: { name: string; count: number; color: string }[];
  ndcClosedTATData: { name: string; count: number; color: string }[];
}

const cleanHex = (hex: string, fallback = "1E3A8A") => {
  if (!hex) return fallback;
  return hex.replace(/^#/, "").trim() || fallback;
};

/**
 * Generates an editable PowerPoint presentation where charts are native Office OpenXML chart objects.
 * Users can right-click any chart in PowerPoint/Google Slides and select "Edit Data" to modify in Excel.
 */
export async function exportAnalyticsEditablePPT(data: AnalyticsEditableData): Promise<void> {
  const pptx = new PptxGenJS();
  pptx.layout = "LAYOUT_WIDE";
  pptx.title = "Analytics Dashboard (Editable Charts)";

  // Define Master Slide with branded header and footer
  pptx.defineSlideMaster({
    title: "MASTER_SLIDE",
    background: { color: "F8FAFC" },
    objects: [
      {
        rect: { x: 0, y: 0, w: "100%", h: 0.8, fill: { color: "1E3A8A" } },
      },
      {
        text: {
          text: "Analytics Dashboard — Performance & Insights",
          options: { x: 0.4, y: 0.1, w: 9.0, h: 0.6, fontSize: 18, color: "FFFFFF", bold: true, valign: "middle" },
        },
      },
      {
        text: {
          text: `Generated on ${formatDate(new Date())}`,
          options: { x: 9.5, y: 0.1, w: 3.4, h: 0.6, fontSize: 11, color: "E2E8F0", align: "right", valign: "middle" },
        },
      },
      {
        text: {
          text: "Editable Presentation — Right-click charts to edit live data",
          options: { x: 0.4, y: 7.15, w: 7.0, h: 0.3, fontSize: 9, color: "94A3B8", italic: true },
        },
      },
      {
        text: {
          text: "Page ",
          options: { x: 11.5, y: 7.15, w: 1.0, h: 0.3, fontSize: 10, color: "64748B", align: "right" },
        },
      },
    ],
    slideNumber: { x: 12.6, y: 7.15, color: "64748B", fontSize: 10 },
  });

  const addHeader = (slide: any, title: string, subtitle?: string) => {
    slide.addText(title, {
      x: 0.4,
      y: 0.95,
      w: 12.5,
      h: 0.35,
      fontSize: 16,
      bold: true,
      color: "0F172A",
    });
    if (subtitle) {
      slide.addText(subtitle, {
        x: 0.4,
        y: 1.25,
        w: 12.5,
        h: 0.25,
        fontSize: 10,
        color: "64748B",
      });
    }
  };

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 1: NDC Status Overview (Left: Pie, Right: Bar)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "NDC Status Overview", "Overall NDC status breakdown and completion turnaround time distribution");

    // 1A. Pie Chart: NDC Status
    const validStatus = data.statusData.filter((d) => d.y > 0);
    if (validStatus.length > 0) {
      const pieChartData = [
        {
          name: "NDC Status",
          labels: validStatus.map((d) => d.name),
          values: validStatus.map((d) => d.y),
        },
      ];
      const pieColors = validStatus.map((d) => cleanHex(d.color));

      slide.addChart(pptx.ChartType.pie, pieChartData, {
        x: 0.4,
        y: 1.6,
        w: 5.9,
        h: 5.2,
        chartColors: pieColors,
        showLegend: true,
        legendPos: "b",
        showPercent: true,
        showValue: true,
        showTitle: true,
        title: "NDC Status Distribution",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
      });
    } else {
      slide.addText("No NDC status data available", { x: 0.4, y: 3.0, w: 5.9, h: 1.0, align: "center", color: "94A3B8" });
    }

    // 1B. Column Chart: NDC Analysis
    const ndcBarLabels = data.ndcAnalysisData.map((d) => d.name);
    const ndcBarValues = data.ndcAnalysisData.map((d) => d.count);
    const ndcBarColors = data.ndcAnalysisData.map((d) => cleanHex(d.fill));

    slide.addChart(
      pptx.ChartType.bar,
      [
        {
          name: "Number of Exited Employees",
          labels: ndcBarLabels,
          values: ndcBarValues,
        },
      ],
      {
        x: 6.7,
        y: 1.6,
        w: 6.2,
        h: 5.2,
        barDir: "col",
        chartColors: ndcBarColors,
        showValue: true,
        showTitle: true,
        title: "NDC Completion Turnaround Time",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Employees",
        showValAxisTitle: true,
        valAxisTitleFontSize: 10,
        catAxisLabelRotate: 325,
      }
    );
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 2: F&F Status Overview (Left: Pie, Right: Bar)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "F&F Status Overview", "Full & Final settlement status breakdown and completion turnaround analysis");

    // 2A. Pie Chart: F&F Status
    const validFnf = data.fnfStatusBreakdownData.entries.filter((d) => d.y > 0);
    if (validFnf.length > 0) {
      const fnfPieData = [
        {
          name: "F&F Status",
          labels: validFnf.map((d) => d.name),
          values: validFnf.map((d) => d.y),
        },
      ];
      const fnfPieColors = validFnf.map((d) => cleanHex(d.color));

      slide.addChart(pptx.ChartType.pie, fnfPieData, {
        x: 0.4,
        y: 1.6,
        w: 5.9,
        h: 5.2,
        chartColors: fnfPieColors,
        showLegend: true,
        legendPos: "b",
        showPercent: true,
        showValue: true,
        showTitle: true,
        title: "F&F Status Breakdown",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
      });
    } else {
      slide.addText("No F&F status data available", { x: 0.4, y: 3.0, w: 5.9, h: 1.0, align: "center", color: "94A3B8" });
    }

    // 2B. Column Chart: F&F Analysis
    const fnfBarLabels = data.fnfAnalysisData.map((d) => d.name);
    const fnfBarValues = data.fnfAnalysisData.map((d) => d.count);
    const fnfBarColors = data.fnfAnalysisData.map((d) => cleanHex(d.fill));

    slide.addChart(
      pptx.ChartType.bar,
      [
        {
          name: "Number of Exited Employees",
          labels: fnfBarLabels,
          values: fnfBarValues,
        },
      ],
      {
        x: 6.7,
        y: 1.6,
        w: 6.2,
        h: 5.2,
        barDir: "col",
        chartColors: fnfBarColors,
        showValue: true,
        showTitle: true,
        title: "F&F Completion Turnaround Time",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Employees",
        showValAxisTitle: true,
        valAxisTitleFontSize: 10,
        catAxisLabelRotate: 325,
      }
    );
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 3: NDC Approval Status & F&F Revision TAT Analysis
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "NDC Approval Status & F&F Revision TAT Analysis", "Departmental approval completion vs pending, and revision turnaround timeline");

    // 3A. Clustered Column: Department Approvals (Completed vs Pending)
    if (data.approvalBottleneckData.length > 0) {
      const depts = data.approvalBottleneckData.map((d) => d.name);
      const multiBarData = [
        {
          name: "Completed",
          labels: depts,
          values: data.approvalBottleneckData.map((d) => d.completed),
        },
        {
          name: "Pending",
          labels: depts,
          values: data.approvalBottleneckData.map((d) => d.pending),
        },
      ];

      slide.addChart(pptx.ChartType.bar, multiBarData, {
        x: 0.4,
        y: 1.6,
        w: 6.1,
        h: 5.2,
        barDir: "col",
        barGrouping: "clustered",
        chartColors: ["10B981", "EF4444"],
        showLegend: true,
        legendPos: "t",
        showValue: true,
        showTitle: true,
        title: "NDC Approval Status by Department",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Cases",
        showValAxisTitle: true,
        valAxisTitleFontSize: 10,
        catAxisLabelRotate: 325,
      });
    } else {
      slide.addText("No department approval data available", { x: 0.4, y: 3.0, w: 6.1, h: 1.0, align: "center", color: "94A3B8" });
    }

    // 3B. Column: F&F Revision TAT Analysis
    const revLabels = data.fnfRevisionTATData.map((d) => d.name);
    const revValues = data.fnfRevisionTATData.map((d) => d.count);
    const revColors = data.fnfRevisionTATData.map((d) => cleanHex(d.fill || d.color));

    slide.addChart(
      pptx.ChartType.bar,
      [
        {
          name: "Number of Employees",
          labels: revLabels,
          values: revValues,
        },
      ],
      {
        x: 6.8,
        y: 1.6,
        w: 6.1,
        h: 5.2,
        barDir: "col",
        chartColors: revColors,
        showValue: true,
        showTitle: true,
        title: "F&F Revision Turnaround Time",
        titleFontSize: 13,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Employees",
        showValAxisTitle: true,
        valAxisTitleFontSize: 10,
        catAxisLabelRotate: 325,
      }
    );
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 4: Monthly Trend NDC Clearance (Multi-series Line)
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "Monthly Trend NDC Clearance", "Monthly comparison between NDC initiated cases and NDC completed cases");

    if (data.monthlyTrendData.length > 0) {
      const months = data.monthlyTrendData.map((d) => d.displayMonth);
      const lineData = [
        {
          name: "NDC Initiated",
          labels: months,
          values: data.monthlyTrendData.map((d) => d.initiated),
        },
        {
          name: "NDC Completed",
          labels: months,
          values: data.monthlyTrendData.map((d) => d.completed),
        },
      ];

      slide.addChart(pptx.ChartType.line, lineData, {
        x: 0.6,
        y: 1.6,
        w: 12.1,
        h: 5.2,
        chartColors: ["1E5A8E", "10B981"],
        showLegend: true,
        legendPos: "t",
        showValue: true,
        lineSize: 3,
        lineDataSymbol: "circle",
        lineDataSymbolSize: 6,
        showTitle: true,
        title: "Initiated vs. Completed Cases by Month",
        titleFontSize: 14,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Cases",
        showValAxisTitle: true,
      });
    } else {
      slide.addText("No monthly trend data available", { x: 0.6, y: 3.0, w: 12.1, h: 1.0, align: "center", color: "94A3B8" });
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 5: F&F Closed TAT Analysis
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "F&F Closed TAT Analysis", "Turnaround time distribution for closed Full & Final settlement cases");

    const labels = data.fnfClosedTATData.map((d) => d.name);
    const values = data.fnfClosedTATData.map((d) => d.count);
    const colors = data.fnfClosedTATData.map((d) => cleanHex(d.color));

    slide.addChart(
      pptx.ChartType.bar,
      [
        {
          name: "Employees",
          labels,
          values,
        },
      ],
      {
        x: 0.8,
        y: 1.6,
        w: 11.7,
        h: 5.2,
        barDir: "col",
        chartColors: colors,
        showValue: true,
        showTitle: true,
        title: "F&F Closed Cases by Turnaround Time",
        titleFontSize: 14,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Employees",
        showValAxisTitle: true,
        catAxisTitle: "TAT Category",
        showCatAxisTitle: true,
      }
    );
  }

  // ───────────────────────────────────────────────────────────────────────────
  // Slide 6: NDC Closed TAT Analysis
  // ───────────────────────────────────────────────────────────────────────────
  {
    const slide = pptx.addSlide({ masterName: "MASTER_SLIDE" });
    addHeader(slide, "NDC Closed TAT Analysis", "Turnaround time distribution for completed No Dues Certificate cases");

    const labels = data.ndcClosedTATData.map((d) => d.name);
    const values = data.ndcClosedTATData.map((d) => d.count);
    const colors = data.ndcClosedTATData.map((d) => cleanHex(d.color));

    slide.addChart(
      pptx.ChartType.bar,
      [
        {
          name: "Employees",
          labels,
          values,
        },
      ],
      {
        x: 0.8,
        y: 1.6,
        w: 11.7,
        h: 5.2,
        barDir: "col",
        chartColors: colors,
        showValue: true,
        showTitle: true,
        title: "NDC Completed Cases by Turnaround Time",
        titleFontSize: 14,
        titleBold: true,
        titleColor: "1E3A8A",
        valAxisTitle: "Number of Employees",
        showValAxisTitle: true,
        catAxisTitle: "TAT Category",
        showCatAxisTitle: true,
      }
    );
  }

  // Save the presentation
  await pptx.writeFile({ fileName: "Analytics_Dashboard_Editable.pptx" });
}
