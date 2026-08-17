/**
 * Utility to format date strings, ISO timestamps, or Date objects into DD-MM-YYYY format.
 * Preserves empty / null / undefined or non-date values (e.g. "Not Applicable", "-").
 */
export function formatDate(dateVal: string | Date | null | undefined): string {
  if (dateVal === null || dateVal === undefined) return "-";

  if (typeof dateVal === "string") {
    const trimmed = dateVal.trim();
    if (!trimmed || trimmed === "-") return "-";

    // If string is already in DD-MM-YYYY format
    if (/^\d{2}-\d{2}-\d{4}$/.test(trimmed)) return trimmed;

    // Handle YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss or YYYY-MM-DD HH:mm:ss
    const ymdMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (ymdMatch) {
      const [, yyyy, mm, dd] = ymdMatch;
      return `${dd}-${mm}-${yyyy}`;
    }
  }

  const d = dateVal instanceof Date ? dateVal : new Date(dateVal);
  if (isNaN(d.getTime())) {
    return typeof dateVal === "string" ? dateVal : "-";
  }

  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();

  return `${day}-${month}-${year}`;
}

/**
 * Safely parse a date string (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, ISO, etc.) or Date object
 * into a local-midnight Date object. Returns null if invalid, empty, or non-date.
 */
export function parseDate(val: string | Date | null | undefined): Date | null {
  if (!val) return null;
  if (val instanceof Date) return isNaN(val.getTime()) ? null : val;
  const str = String(val).trim();
  if (!str || str === "-" || str.toLowerCase() === "not applicable") return null;

  // Handle YYYY-MM-DD or YYYY/MM/DD
  const ymdMatch = str.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
  if (ymdMatch) {
    const [, yyyy, mm, dd] = ymdMatch;
    return new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  }

  // Handle DD-MM-YYYY or DD/MM/YYYY
  const dmyMatch = str.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
  if (dmyMatch) {
    const [, dd, mm, yyyy] = dmyMatch;
    return new Date(Number(yyyy), Number(mm) - 1, Number(dd));
  }

  const d = new Date(str);
  if (isNaN(d.getTime())) return null;
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/**
 * Check if a property key represents a date field.
 */
export function isDateKey(key: string): boolean {
  const lowerKey = key.toLowerCase();
  return (
    lowerKey.endsWith("date") ||
    lowerKey.endsWith("_at") ||
    lowerKey === "date"
  );
}

