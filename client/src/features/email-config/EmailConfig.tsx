import { useState, useEffect } from "react";
import axios from "../../lib/axios";
import { Mail, Plus, Trash2, Pencil, X, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { LoadingScreen } from "../../components/common/LoadingScreen";
import { toast } from "sonner";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";

interface EmailRecipient {
  id: string;
  name: string;
  email: string;
  department: string;
  role: string;
}

const DEPARTMENTS = [
  "RM",
  "IT",
  "Abex",
  "Telecom",
  "Store",
  "Safety",
  "Administration",
  "Security",
  "HR",
  "GCC HR",
  "Business Specific",
  "Final Abex",
  "Legatrix",
  "F&F Team",
];

const EMPTY_FORM = { name: "", email: "", department: "", role: "" };

export function EmailConfig() {
  const [recipients, setRecipients] = useState<EmailRecipient[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Add form state
  const [isAdding, setIsAdding] = useState(false);
  const [newRecipient, setNewRecipient] = useState<Omit<EmailRecipient, "id">>(EMPTY_FORM);

  // Inline-edit state – stores the id being edited + a mutable copy of the row
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<EmailRecipient, "id">>(EMPTY_FORM);

  // Delete confirm
  const [recipientToDelete, setRecipientToDelete] = useState<string | null>(null);

  // Saving spinner for inline edit
  const [isSaving, setIsSaving] = useState(false);

  // Pagination states
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);

  // Search state
  const [search, setSearch] = useState("");

  // Filter search
  const filteredRecipients = recipients.filter((r) => {
    const term = search.toLowerCase();
    return (
      r.name.toLowerCase().includes(term) ||
      r.email.toLowerCase().includes(term) ||
      r.department.toLowerCase().includes(term) ||
      (r.role || "").toLowerCase().includes(term)
    );
  });

  // Pagination calculation
  const totalPages = Math.ceil(filteredRecipients.length / limit);
  const paginatedRecipients = filteredRecipients.slice((page - 1) * limit, page * limit);

  useEffect(() => {
    if (page > totalPages && totalPages > 0) {
      setPage(totalPages);
    }
  }, [filteredRecipients.length, totalPages, page]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = () => {
    axios.get("/api/v1/email-recipients").then((res) => {
      const data = res.data?.data || res.data;
      setRecipients(Array.isArray(data) ? data : []);
      setIsLoading(false);
    });
  };

  // ── ADD ──────────────────────────────────────────────
  const handleAddRecipient = () => {
    if (!newRecipient.name || !newRecipient.email || !newRecipient.department) {
      toast.error("Name, Email, and Department are required.");
      return;
    }
    // Client-side duplicate check (per department)
    const emailLower = newRecipient.email.trim().toLowerCase();
    const deptLower = newRecipient.department.trim().toLowerCase();
    const isDuplicate = recipients.some(
      (r) => r.email.toLowerCase() === emailLower && (r.department || "").trim().toLowerCase() === deptLower
    );
    if (isDuplicate) {
      toast.error("A recipient with this email already exists in this department.");
      return;
    }
    axios.post("/api/v1/email-recipients", { ...newRecipient, email: emailLower })
      .then(() => {
        fetchData();
        setNewRecipient(EMPTY_FORM);
        setIsAdding(false);
        toast.success("Recipient added successfully.");
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail || "Failed to add recipient.";
        toast.error(detail);
      });
  };

  // ── EDIT ─────────────────────────────────────────────
  const startEdit = (recipient: EmailRecipient) => {
    setEditingId(recipient.id);
    setEditDraft({
      name: recipient.name,
      email: recipient.email,
      department: recipient.department,
      role: recipient.role,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft(EMPTY_FORM);
  };

  const saveEdit = () => {
    if (!editDraft.name || !editDraft.email || !editDraft.department) {
      toast.error("Name, Email, and Department are required.");
      return;
    }
    // Client-side duplicate check – exclude the row being edited (per department)
    const emailLower = editDraft.email.trim().toLowerCase();
    const deptLower = editDraft.department.trim().toLowerCase();
    const isDuplicate = recipients.some(
      (r) =>
        r.email.toLowerCase() === emailLower &&
        (r.department || "").trim().toLowerCase() === deptLower &&
        r.id !== editingId
    );
    if (isDuplicate) {
      toast.error("Another recipient with this email already exists in this department.");
      return;
    }
    setIsSaving(true);
    axios.put(`/api/v1/email-recipients/${editingId}`, { ...editDraft, email: emailLower })
      .then(() => {
        fetchData();
        setEditingId(null);
        setEditDraft(EMPTY_FORM);
        toast.success("Recipient updated successfully.");
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail || "Failed to update recipient.";
        toast.error(detail);
      })
      .finally(() => setIsSaving(false));
  };

  // ── DELETE ───────────────────────────────────────────
  const confirmRemoveRecipient = () => {
    if (recipientToDelete) {
      axios.delete(`/api/v1/email-recipients/${recipientToDelete}`).then(() => {
        fetchData();
        setRecipientToDelete(null);
        toast.success("Recipient removed successfully.");
      }).catch(() => toast.error("Failed to remove recipient."));
    }
  };

  if (isLoading) return <LoadingScreen />;

  return (
    <div className="p-8 space-y-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Email Configuration</h1>
        <p className="text-muted-foreground mt-2">Manage Email Recipients for NDC Notifications</p>
      </div>

      <div className="bg-card rounded-[4px] border border-border flex flex-col overflow-hidden">
        {/* Table Controls */}
        <div className="p-4 border-b border-border bg-muted/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by Name, Email or Department..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
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
            onClick={() => { setIsAdding(!isAdding); setNewRecipient(EMPTY_FORM); }}
            className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-[4px] transition-colors shadow-sm shrink-0"
          >
            <Plus className="w-4 h-4" />
            Add Recipient
          </button>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Email</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Department</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {paginatedRecipients.map((recipient) => {
                return (
                  <tr key={recipient.id} className="hover:bg-muted/50 transition-colors">
                    {/* Name */}
                    <td className="px-4 py-2.5 text-sm font-medium text-foreground">
                      {recipient.name}
                    </td>
                    {/* Email */}
                    <td className="px-4 py-2.5 text-sm">
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-muted-foreground" />
                        {recipient.email}
                      </div>
                    </td>
                    {/* Department */}
                    <td className="px-4 py-2.5 text-sm">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-[4px] text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        {recipient.department}
                      </span>
                    </td>
                    {/* Role */}
                    <td className="px-4 py-2.5 text-sm text-muted-foreground">
                      {recipient.role || "—"}
                    </td>
                    {/* Actions */}
                    <td className="px-4 py-2.5 text-sm">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => startEdit(recipient)}
                          className="p-1.5 rounded-[4px] bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                          title="Edit Recipient"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setRecipientToDelete(recipient.id)}
                          className="p-1.5 rounded-[4px] bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                          title="Remove Recipient"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {filteredRecipients.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    {search ? "No recipients match your search." : "No recipients configured. Click \"Add Recipient\" to get started."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Client-side Pagination */}
        <div className="px-6 py-4 border-t border-border flex flex-wrap items-center justify-between gap-4 bg-card">
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-sm text-muted-foreground">
              Showing {filteredRecipients.length > 0 ? (page - 1) * limit + 1 : 0} to {Math.min(page * limit, filteredRecipients.length)} of {filteredRecipients.length} records
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

      {/* Delete confirmation */}
      <AlertDialog open={!!recipientToDelete} onOpenChange={(open) => !open && setRecipientToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this recipient?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The recipient will be permanently removed from the email configuration.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmRemoveRecipient} className="bg-red-600 text-white hover:bg-red-700">
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Add Recipient Modal */}
      <Dialog open={isAdding} onOpenChange={(open) => {
        setIsAdding(open);
        if (!open) setNewRecipient(EMPTY_FORM);
      }}>
        <DialogContent className="max-w-md p-6 bg-card border border-border">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Add Recipient</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newRecipient.name}
                onChange={(e) => setNewRecipient({ ...newRecipient, name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="Enter name"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={newRecipient.email}
                onChange={(e) => setNewRecipient({ ...newRecipient, email: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="email@adani.com"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Department <span className="text-red-500">*</span>
              </label>
              <select
                value={newRecipient.department}
                onChange={(e) => setNewRecipient({ ...newRecipient, department: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
              >
                <option value="">Select Department</option>
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Role</label>
              <input
                type="text"
                value={newRecipient.role}
                onChange={(e) => setNewRecipient({ ...newRecipient, role: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="e.g., Manager, Head"
              />
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={() => { setIsAdding(false); setNewRecipient(EMPTY_FORM); }}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddRecipient}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium rounded-[4px] transition-colors"
              >
                Add Recipient
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Recipient Modal */}
      <Dialog open={editingId !== null} onOpenChange={(open) => { if (!open) cancelEdit(); }}>
        <DialogContent className="max-w-md p-6 bg-card border border-border">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Edit Recipient</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={editDraft.name}
                onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="Enter name"
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={editDraft.email}
                onChange={(e) => setEditDraft({ ...editDraft, email: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="email@adani.com"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">
                Department <span className="text-red-500">*</span>
              </label>
              <select
                value={editDraft.department}
                onChange={(e) => setEditDraft({ ...editDraft, department: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
              >
                <option value="">Select Department</option>
                {DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Role</label>
              <input
                type="text"
                value={editDraft.role}
                onChange={(e) => setEditDraft({ ...editDraft, role: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm text-foreground"
                placeholder="e.g., Manager, Head"
              />
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={cancelEdit}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveEdit}
                disabled={isSaving}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {isSaving ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
