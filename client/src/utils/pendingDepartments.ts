import { NDCRecord } from "../types";
import { parseDate } from "./dateFormatter";

const normalizeStatus = (s: string) => (s || "").trim().toLowerCase();

export const getPendingDepartments = (record: NDCRecord): string => {
  if (record.ndcStage === "NDC Completed") return "-";

  const stages: { key: keyof NDCRecord; label: string }[] = [
    { key: "rmApprovalStatus", label: "RM" },
    { key: "itApprovalStatus", label: "IT" },
    { key: "abexApprovalStatus", label: "ABEX" },
    { key: "telecomApprovalStatus", label: "Telecom" },
    { key: "storeApprovalStatus", label: "Store" },
    { key: "safetyApprovalStatus", label: "Safety" },
    { key: "administrationApprovalStatus", label: "Administration" },
    { key: "securityApprovalStatus", label: "Security" },
    { key: "hrApprovalStatus", label: "HR" },
    { key: "gccHrApprovalStatus", label: "GCC HR" },
    { key: "businessSpecificApprovalStatus", label: "Business Specific" },
    { key: "finalAbexApprovalStatus", label: "Final ABEX" },
    { key: "legatrixApprovalStatus", label: "Legatrix" },
  ];

  const pendingList = stages
    .filter(({ key, label }) => {
      const status = normalizeStatus(record[key] as string);
      const isPending = status === "pending" || status === "in progress" || status === "open";
      if (!isPending) return false;
      if (label === "IT" || label === "Security") {
        const lwd = parseDate(record.lastWorkingDate);
        if (!lwd) return false;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        lwd.setHours(0, 0, 0, 0);
        const daysUntilLWD = Math.round((lwd.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        if (daysUntilLWD > 3) return false;
      }
      return true;
    })
    .map(({ label }) => label);

  return pendingList.length > 0 ? pendingList.join(", ") : "-";
};
