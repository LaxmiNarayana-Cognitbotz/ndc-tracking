import { NDCRecord } from "../types";

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
    .filter(({ key }) => {
      const status = normalizeStatus(record[key] as string);
      return status === "pending" || status === "in progress" || status === "open";
    })
    .map(({ label }) => label);

  return pendingList.length > 0 ? pendingList.join(", ") : "-";
};
