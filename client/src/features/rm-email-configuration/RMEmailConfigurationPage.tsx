import { useState, useEffect } from "react";
import axios from "../../lib/axios";
import { toast } from "sonner";
import {
  Search,
  Trash2,
  Download,
  Upload,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Info,
  X,
  FileSpreadsheet,
  Plus,
  Pencil,
  Mail
} from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from "../../components/ui/dialog";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../../components/ui/alert-dialog";

import { Progress } from "../../components/ui/progress";

interface RMEmailConfiguration {
  id: number;
  rm_name: string;
  email: string;
  created_at: string | null;
  updated_at: string | null;
}

interface RowError {
  row: number;
  message: string;
}

interface ImportSummary {
  success: boolean;
  inserted: number;
  skipped: number;
  failed: number;
  errors: RowError[];
}

export function RMEmailConfigurationPage() {
  const [data, setData] = useState<RMEmailConfiguration[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Pagination states
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // Search states
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Modals states
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [configToDelete, setConfigToDelete] = useState<number | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Add RM states
  const [addForm, setAddForm] = useState({ rm_name: "", email: "" });
  const [addErrors, setAddErrors] = useState({ rm_name: "", email: "" });
  const [isAdding, setIsAdding] = useState(false);

  // Edit RM states
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ id: 0, rm_name: "", email: "" });
  const [editErrors, setEditErrors] = useState({ rm_name: "", email: "" });
  const [isEditing, setIsEditing] = useState(false);

  // Import file states
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);

  // Search Debouncing (400ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [search]);

  // Load Data
  const fetchData = () => {
    setIsLoading(true);
    axios.get("/api/v1/rm-email-configuration", {
      params: {
        page,
        limit,
        search: debouncedSearch
      }
    })
    .then((res) => {
      const responseData = res.data;
      if (responseData) {
        setData(responseData.data || []);
        setTotal(responseData.total || 0);
        setTotalPages(responseData.totalPages || 0);
      }
    })
    .catch((err) => {
      const errMsg = err.response?.data?.detail || err.message || "Failed to load email configurations.";
      toast.error(errMsg);
    })
    .finally(() => {
      setIsLoading(false);
    });
  };

  useEffect(() => {
    fetchData();
  }, [page, limit, debouncedSearch]);

  // Download Sample Excel
  const handleDownloadSample = () => {
    axios.get("/api/v1/rm-email-configuration/sample", { responseType: "blob" })
      .then((res) => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "sample_rm_email_configuration.xlsx");
        document.body.appendChild(link);
        link.click();
        link.remove();
        toast.success("Sample Excel downloaded.");
      })
      .catch(() => {
        toast.error("Failed to download sample Excel file.");
      });
  };

  // Upload Excel File
  const handleUploadFile = () => {
    if (!fileToUpload) {
      toast.error("Please select an Excel file to upload.");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setImportSummary(null);

    const formData = new FormData();
    formData.append("file", fileToUpload);

    axios.post("/api/v1/rm-email-configuration/import", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        const percent = Math.round(
          (progressEvent.loaded * 100) / (progressEvent.total || progressEvent.loaded)
        );
        setUploadProgress(percent);
      },
    })
    .then((res) => {
      setImportSummary(res.data);
      if (res.data.failed > 0) {
        toast.warning(`Import completed with ${res.data.failed} row error(s).`);
      } else {
        toast.success(`Successfully imported ${res.data.inserted} record(s).`);
      }
      setFileToUpload(null);
      fetchData();
    })
    .catch((err) => {
      const errMsg = err.response?.data?.detail || err.message || "Failed to import Excel file.";
      toast.error(errMsg);
    })
    .finally(() => {
      setUploading(false);
    });
  };

  // Add RM
  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    let hasError = false;
    const errors = { rm_name: "", email: "" };
    
    if (!addForm.rm_name.trim()) {
      errors.rm_name = "RM Name is required";
      hasError = true;
    }
    
    if (!addForm.email.trim()) {
      errors.email = "Email is required";
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(addForm.email)) {
      errors.email = "Invalid email format";
      hasError = true;
    }
    
    setAddErrors(errors);
    
    if (hasError) return;
    
    setIsAdding(true);
    axios.post("/api/v1/rm-email-configuration", addForm, {
      // @ts-ignore - custom config property
      skipGlobalToast: true
    })
      .then((res) => {
        toast.success(res.data.message || "RM added successfully");
        setIsAddOpen(false);
        setAddForm({ rm_name: "", email: "" });
        fetchData();
      })
      .catch((err) => {
        const errMsg = err.response?.data?.message || err.response?.data?.detail || err.message || "Failed to add RM";
        toast.error(errMsg);
      })
      .finally(() => {
        setIsAdding(false);
      });
  };

  // Edit RM
  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    let hasError = false;
    const errors = { rm_name: "", email: "" };
    
    if (!editForm.rm_name.trim()) {
      errors.rm_name = "RM Name is required";
      hasError = true;
    }
    
    if (!editForm.email.trim()) {
      errors.email = "Email is required";
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editForm.email)) {
      errors.email = "Invalid email format";
      hasError = true;
    }
    
    setEditErrors(errors);
    
    if (hasError) return;
    
    setIsEditing(true);
    axios.put(`/api/v1/rm-email-configuration/${editForm.id}`, {
      rm_name: editForm.rm_name,
      email: editForm.email
    }, {
      // @ts-ignore - custom config property
      skipGlobalToast: true
    })
      .then((res) => {
        toast.success(res.data.message || "RM updated successfully");
        setIsEditOpen(false);
        setEditForm({ id: 0, rm_name: "", email: "" });
        fetchData();
      })
      .catch((err) => {
        const errMsg = err.response?.data?.message || err.response?.data?.detail || err.message || "Failed to update RM";
        toast.error(errMsg);
      })
      .finally(() => {
        setIsEditing(false);
      });
  };

  // Delete RM
  const confirmDelete = () => {
    if (configToDelete === null) return;

    axios.delete(`/api/v1/rm-email-configuration/${configToDelete}`)
      .then(() => {
        toast.success("RM email configuration deleted.");
        setConfigToDelete(null);
        fetchData();
      })
      .catch((err) => {
        const errMsg = err.response?.data?.detail || err.message || "Failed to delete record.";
        toast.error(errMsg);
      });
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">RM Email Master</h1>
          <p className="text-muted-foreground mt-1">Manage relationship managers and their emails for workflow alerts</p>
        </div>
        <div className="flex flex-row items-center gap-3 shrink-0">
          <button
            onClick={handleDownloadSample}
            className="flex items-center gap-2 px-4 py-2 border border-border bg-card hover:bg-muted text-foreground text-sm font-medium rounded-[4px] transition-colors shrink-0"
          >
            <Download className="w-4 h-4 text-muted-foreground" />
            Download Sample Excel
          </button>
          <button
            onClick={() => {
              setIsImportOpen(true);
              setImportSummary(null);
              setFileToUpload(null);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-[4px] transition-colors shadow-sm shrink-0"
          >
            <Upload className="w-4 h-4" />
            Import Excel
          </button>
        </div>
      </div>

      <div className="bg-card rounded-[4px] border border-border flex flex-col overflow-hidden">
        {/* Table Controls */}
        <div className="p-4 border-b border-border bg-muted/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by RM Name or Email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 w-full border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm placeholder:text-muted-foreground"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <button
            onClick={() => {
              setIsAddOpen(true);
              setAddForm({ rm_name: "", email: "" });
              setAddErrors({ rm_name: "", email: "" });
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-[4px] transition-colors shadow-sm shrink-0"
          >
            <Plus className="w-4 h-4" />
            Add RM
          </button>
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">RM Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {isLoading ? (
                <tr>
                  <td colSpan={3} className="py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                      <span>Loading configurations...</span>
                    </div>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={3} className="py-16 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Info className="w-10 h-10 text-muted-foreground/50" />
                      <span className="font-medium text-base">No records found</span>
                      <span className="text-sm text-muted-foreground max-w-xs leading-relaxed">
                        {debouncedSearch ? "Try adjusting your search criteria" : "Click 'Import Excel' to populate configurations"}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                data.map((row) => (
                  <tr key={row.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-2.5 text-sm font-medium text-foreground whitespace-nowrap">{row.rm_name}</td>
                    <td className="px-4 py-2.5 text-sm whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-muted-foreground" />
                        {row.email}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-sm whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => {
                            setEditForm({ id: row.id, rm_name: row.rm_name, email: row.email });
                            setEditErrors({ rm_name: "", email: "" });
                            setIsEditOpen(true);
                          }}
                          className="p-1.5 rounded-[4px] bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                          title="Edit Record"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setConfigToDelete(row.id)}
                          className="p-1.5 rounded-[4px] bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                          title="Delete Record"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server side Pagination */}
        <div className="px-6 py-4 border-t border-border flex flex-wrap items-center justify-between gap-4 bg-card">
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-sm text-muted-foreground">
              Showing {data.length > 0 ? (page - 1) * limit + 1 : 0} to {Math.min(page * limit, total)} of {total} records
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>Rows per page:</span>
              <select
                value={limit}
                onChange={(e) => {
                  setLimit(Number(e.target.value));
                  setPage(1);
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
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={page === 1}
              className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground bg-card"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-foreground">
              Page {page} of {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={page === totalPages || totalPages === 0}
              className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground bg-card"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Excel Import Modal */}
      <Dialog open={isImportOpen} onOpenChange={(open) => {
        if (!uploading) {
          setIsImportOpen(open);
          if (!open) {
            setFileToUpload(null);
            setImportSummary(null);
          }
        }
      }}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Import RM Email Master</DialogTitle>
          </DialogHeader>
          <div className="space-y-5 pt-4">
            <div className="flex flex-col items-center justify-center border-2 border-dashed border-border hover:border-primary/50 transition-colors p-8 rounded-[4px] cursor-pointer bg-muted/10 relative">
              <input
                type="file"
                accept=".xlsx, .xls"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setFileToUpload(e.target.files[0]);
                    setImportSummary(null);
                  }
                }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                disabled={uploading}
              />
              <FileSpreadsheet className="w-10 h-10 text-muted-foreground/60 mb-2" />
              <span className="text-sm font-medium text-foreground">
                {fileToUpload ? fileToUpload.name : "Click or drag to select Excel file"}
              </span>
              <span className="text-xs text-muted-foreground mt-1">Accepts only .xlsx and .xls formats</span>
            </div>

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-muted-foreground">
                  <span>Uploading Excel File...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-1.5" />
              </div>
            )}

            {importSummary && (
              <div className="space-y-4 pt-4 border-t border-border">
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 bg-green-50/50 border border-green-200 rounded-[4px] dark:bg-green-950/20 dark:border-green-900">
                    <div className="text-xl font-bold text-green-600 dark:text-green-400">{importSummary.inserted}</div>
                    <div className="text-xs text-muted-foreground font-medium">Inserted</div>
                  </div>
                  <div className="p-3 bg-blue-50/50 border border-blue-200 rounded-[4px] dark:bg-blue-950/20 dark:border-blue-900">
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{importSummary.skipped}</div>
                    <div className="text-xs text-muted-foreground font-medium">Skipped</div>
                  </div>
                  <div className="p-3 bg-red-50/50 border border-red-200 rounded-[4px] dark:bg-red-950/20 dark:border-red-900">
                    <div className="text-xl font-bold text-red-600 dark:text-red-400">{importSummary.failed}</div>
                    <div className="text-xs text-muted-foreground font-medium">Failed</div>
                  </div>
                </div>

                {importSummary.errors && importSummary.errors.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-y-auto border border-border rounded-[4px] p-3 bg-muted/30">
                    <div className="text-xs font-bold text-foreground flex items-center gap-1">
                      <Info className="w-3.5 h-3.5 text-red-500" />
                      Row Validation Failures:
                    </div>
                    <ul className="space-y-1.5 pl-1.5 list-none">
                      {importSummary.errors.map((err, i) => (
                        <li key={i} className="text-xs text-red-600 dark:text-red-400 flex items-start gap-1">
                          <span className="font-semibold shrink-0">Row {err.row}:</span>
                          <span>{err.message}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-3 justify-end pt-4 border-t border-border">
              <button
                onClick={() => setIsImportOpen(false)}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
                disabled={uploading}
              >
                Close
              </button>
              <button
                onClick={handleUploadFile}
                disabled={!fileToUpload || uploading}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
                Import Rows
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add RM Modal */}
      <Dialog open={isAddOpen} onOpenChange={(open) => !isAdding && setIsAddOpen(open)}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Add RM Email</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddSubmit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">RM Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={addForm.rm_name}
                onChange={(e) => {
                  setAddForm({ ...addForm, rm_name: e.target.value });
                  if (addErrors.rm_name) setAddErrors({ ...addErrors, rm_name: "" });
                }}
                className={`w-full px-3 py-2 border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 ${addErrors.rm_name ? 'border-red-500 focus:ring-red-500' : 'border-border focus:ring-primary'}`}
                placeholder="Enter RM Name"
                disabled={isAdding}
              />
              {addErrors.rm_name && <p className="text-xs text-red-500">{addErrors.rm_name}</p>}
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Email <span className="text-red-500">*</span></label>
              <input
                type="email"
                value={addForm.email}
                onChange={(e) => {
                  setAddForm({ ...addForm, email: e.target.value });
                  if (addErrors.email) setAddErrors({ ...addErrors, email: "" });
                }}
                className={`w-full px-3 py-2 border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 ${addErrors.email ? 'border-red-500 focus:ring-red-500' : 'border-border focus:ring-primary'}`}
                placeholder="Enter Email Address"
                disabled={isAdding}
              />
              {addErrors.email && <p className="text-xs text-red-500">{addErrors.email}</p>}
            </div>
            
            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
                disabled={isAdding}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isAdding}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {isAdding && <Loader2 className="w-4 h-4 animate-spin" />}
                Add RM
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit RM Modal */}
      <Dialog open={isEditOpen} onOpenChange={(open) => !isEditing && setIsEditOpen(open)}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Edit RM Email</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">RM Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={editForm.rm_name}
                onChange={(e) => {
                  setEditForm({ ...editForm, rm_name: e.target.value });
                  if (editErrors.rm_name) setEditErrors({ ...editErrors, rm_name: "" });
                }}
                className={`w-full px-3 py-2 border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 ${editErrors.rm_name ? 'border-red-500 focus:ring-red-500' : 'border-border focus:ring-primary'}`}
                placeholder="Enter RM Name"
                disabled={isEditing}
              />
              {editErrors.rm_name && <p className="text-xs text-red-500">{editErrors.rm_name}</p>}
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Email <span className="text-red-500">*</span></label>
              <input
                type="email"
                value={editForm.email}
                onChange={(e) => {
                  setEditForm({ ...editForm, email: e.target.value });
                  if (editErrors.email) setEditErrors({ ...editErrors, email: "" });
                }}
                className={`w-full px-3 py-2 border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 ${editErrors.email ? 'border-red-500 focus:ring-red-500' : 'border-border focus:ring-primary'}`}
                placeholder="Enter Email Address"
                disabled={isEditing}
              />
              {editErrors.email && <p className="text-xs text-red-500">{editErrors.email}</p>}
            </div>
            
            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={() => setIsEditOpen(false)}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
                disabled={isEditing}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isEditing}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {isEditing && <Loader2 className="w-4 h-4 animate-spin" />}
                Save Changes
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={configToDelete !== null} onOpenChange={(open) => !open && setConfigToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete RM Email Master?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this record? This action cannot be undone and this relationship manager will stop receiving workflow alerts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-red-600 text-white hover:bg-red-700">
              Confirm Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
