import { useState } from "react";
import { Image as ImageIcon, BarChart3, X, Loader2 } from "lucide-react";

interface PPTExportChoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExportDashboard: () => Promise<void>;
  onExportEditable: () => Promise<void>;
}

export function PPTExportChoiceModal({
  isOpen,
  onClose,
  onExportDashboard,
  onExportEditable,
}: PPTExportChoiceModalProps) {
  const [loadingType, setLoadingType] = useState<"dashboard" | "editable" | null>(null);

  if (!isOpen) return null;

  const handleSelect = async (type: "dashboard" | "editable") => {
    setLoadingType(type);
    try {
      if (type === "dashboard") {
        await onExportDashboard();
      } else {
        await onExportEditable();
      }
      onClose();
    } catch (err: any) {
      console.error("PPT export failed:", err);
      alert("Failed to export PPT: " + (err?.message || err?.toString() || "Unknown error"));
    } finally {
      setLoadingType(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div 
        className="bg-card text-foreground border border-border rounded-[4px] shadow-xl w-full max-w-lg flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header matching project DataModal / Card header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
          <div>
            <h2 className="text-base font-semibold text-foreground">Export Presentation</h2>
            <p className="text-xs text-muted-foreground mt-0.5">Select your preferred PowerPoint export format</p>
          </div>
          <button
            onClick={onClose}
            disabled={loadingType !== null}
            className="p-1 rounded-[4px] hover:bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content / Options */}
        <div className="p-6 space-y-3">
          {/* Option 1: Dashboard PPT (Standard View) */}
          <button
            onClick={() => handleSelect("dashboard")}
            disabled={loadingType !== null}
            className="w-full text-left p-4 rounded-[4px] border border-border hover:border-[#003b70] hover:bg-muted/40 transition-all flex items-start gap-3.5 group disabled:opacity-60 cursor-pointer"
          >
            <div className="w-9 h-9 rounded-[4px] bg-[#003b70]/10 text-[#003b70] flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-[#003b70]/20 transition-colors">
              <ImageIcon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-foreground group-hover:text-[#003b70] transition-colors">
                  Dashboard PPT
                </span>
                <span className="text-[10px] font-medium px-2 py-0.5 bg-muted text-muted-foreground border border-border rounded-[2px]">
                  Visual Snapshot
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Exact visual mirror of web dashboard with all colors, cards, and formatting (image-based).
              </p>
            </div>
            {loadingType === "dashboard" ? (
              <Loader2 className="w-4 h-4 text-[#003b70] animate-spin shrink-0 self-center" />
            ) : (
              <span className="text-xs font-medium text-[#003b70] opacity-0 group-hover:opacity-100 transition-opacity self-center shrink-0">
                Export &rarr;
              </span>
            )}
          </button>

          {/* Option 2: Editable PPT (Native Charts) */}
          <button
            onClick={() => handleSelect("editable")}
            disabled={loadingType !== null}
            className="w-full text-left p-4 rounded-[4px] border border-border hover:border-[#c55a11] hover:bg-muted/40 transition-all flex items-start gap-3.5 group disabled:opacity-60 cursor-pointer"
          >
            <div className="w-9 h-9 rounded-[4px] bg-[#c55a11]/10 text-[#c55a11] flex items-center justify-center shrink-0 mt-0.5 group-hover:bg-[#c55a11]/20 transition-colors">
              <BarChart3 className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-semibold text-foreground group-hover:text-[#c55a11] transition-colors">
                  Editable PPT
                </span>
                <span className="text-[10px] font-medium px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800 rounded-[2px]">
                  Editable Charts
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Generates native PowerPoint charts (Pie, Bar, Line). Right-click charts in PowerPoint to edit data in Excel.
              </p>
            </div>
            {loadingType === "editable" ? (
              <Loader2 className="w-4 h-4 text-[#c55a11] animate-spin shrink-0 self-center" />
            ) : (
              <span className="text-xs font-medium text-[#c55a11] opacity-0 group-hover:opacity-100 transition-opacity self-center shrink-0">
                Export &rarr;
              </span>
            )}
          </button>
        </div>

        {/* Footer matching corporate style */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-muted/20 text-xs">
          <span className="text-muted-foreground">
            Both formats export identical underlying metrics
          </span>
          <button
            type="button"
            onClick={onClose}
            disabled={loadingType !== null}
            className="px-4 py-1.5 border border-border text-foreground hover:bg-muted text-xs font-medium rounded-[4px] transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
