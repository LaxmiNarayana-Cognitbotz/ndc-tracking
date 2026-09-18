import { useState } from "react";
import { Presentation } from "lucide-react";

interface PPTDownloadButtonProps {
  onDownload?: () => Promise<void>;
  onClick?: () => void;
}

export function PPTDownloadButton({ onDownload, onClick }: PPTDownloadButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (onClick) {
      onClick();
      return;
    }
    if (!onDownload) return;
    setLoading(true);
    try {
      await onDownload();
    } catch (err: any) {
      console.error("PPT generation error:", err);
      alert("Failed to generate PPT: " + (err.message || err.toString() || "Unknown error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-[#c55a11] text-white rounded-[4px] hover:bg-[#a34a0e] transition-colors disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
      title="Download as PowerPoint"
    >
      {loading ? (
        <>
          <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          Generating...
        </>
      ) : (
        <>
          <Presentation className="w-4 h-4" />
          Download PPT
        </>
      )}
    </button>
  );
}
