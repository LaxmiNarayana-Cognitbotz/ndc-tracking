import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import api from "../../lib/axios";
import { formatDate } from "../../utils/dateFormatter";
import {
  Trash2, Shield, Mail, Key,
  Loader2, Search, RefreshCw, Info, X, Plus, Pencil, Eye, EyeOff,
  ChevronLeft, ChevronRight
} from "lucide-react";
import { toast } from "sonner";

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

interface UserRecord {
  id: number;
  email: string;
  name: string;
  role: "super_admin" | "admin";
  status: "approved" | "pending" | "rejected";
  requested_at?: string;
  approved_at?: string;
  approved_by?: string;
  notes?: string;
}

export function UserManagement() {
  const { user: currentUser, logout } = useAuth();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // Modals state
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserRecord | null>(null);
  const [userToDelete, setUserToDelete] = useState<string | null>(null);

  // Form states
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"admin" | "super_admin">("admin");
  const [status, setStatus] = useState<"approved" | "pending" | "rejected">("approved");
  const [password, setPassword] = useState("");
  const [showAddPassword, setShowAddPassword] = useState(false);
  const [showEditPassword, setShowEditPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const res = await api.get<any>("api/admin/users");
      const data = res.data?.data || res.data;
      setUsers(Array.isArray(data) ? data : []);
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.response?.data?.detail || "Failed to load users");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser?.role === "super_admin") {
      fetchUsers();
    }
  }, [currentUser]);

  // Deny access if not super_admin
  if (currentUser?.role !== "super_admin") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] p-6 text-center">
        <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center mb-4">
          <Shield size={32} />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">Access Denied</h2>
        <p className="text-muted-foreground max-w-md">
          Only Super Administrators have permission to view and manage users on this platform.
        </p>
      </div>
    );
  }

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // if (!email.trim().toLowerCase().endsWith("@adani.com")) {
    //   toast.error("Email must end with @adani.com");
    //   return;
    // }
    if (!password.trim()) {
      toast.error("Password is required for new users");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("api/admin/users", {
        email: email.trim().toLowerCase(),
        name: name.trim(),
        role,
        password: password.trim(),
      });
      toast.success("User added successfully");
      setIsAddOpen(false);
      resetForm();
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.response?.data?.detail || "Failed to add user");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    setIsSubmitting(true);
    try {
      const isPasswordChanged = Boolean(password.trim());
      const isSelf = currentUser?.email.toLowerCase() === selectedUser.email.toLowerCase();

      await api.put(`api/admin/users/${selectedUser.email}`, {
        name: name.trim(),
        role,
        status,
        password: password.trim() ? password.trim() : undefined,
      });

      if (isPasswordChanged && isSelf) {
        toast.success("Password updated successfully! Logging out to re-authenticate...");
        setIsEditOpen(false);
        resetForm();
        setTimeout(async () => {
          await logout();
        }, 1200);
        return;
      }

      toast.success("User updated successfully");
      setIsEditOpen(false);
      resetForm();
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.response?.data?.detail || "Failed to update user");
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!userToDelete) return;
    try {
      await api.delete(`api/admin/users/${userToDelete}`);
      toast.success("User deleted successfully");
      setUserToDelete(null);
      fetchUsers();
    } catch (err: any) {
      toast.error(err.response?.data?.message || err.response?.data?.detail || "Failed to delete user");
    }
  };

  const openEdit = (user: UserRecord) => {
    setSelectedUser(user);
    setName(user.name || "");
    setEmail(user.email);
    setRole(user.role);
    setStatus(user.status);
    setPassword("");
    setIsEditOpen(true);
  };

  const resetForm = () => {
    setName("");
    setEmail("");
    setRole("admin");
    setStatus("approved");
    setPassword("");
    setSelectedUser(null);
    setShowAddPassword(false);
    setShowEditPassword(false);
  };

  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);

  const filteredUsers = users.filter(u =>
    u.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / itemsPerPage));
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedUsers = filteredUsers.slice(startIndex, startIndex + itemsPerPage);

  const getRoleBadge = (role: string) => {
    if (role === "super_admin") {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[4px] text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200">
          Super Admin
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-[4px] text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
        Admin
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    if (status === "approved") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-[4px] text-xs font-medium bg-green-50 text-green-700 border border-green-200">
          Approved
        </span>
      );
    }
    if (status === "pending") {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-[4px] text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
          Pending
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-[4px] text-xs font-medium bg-red-50 text-red-700 border border-red-200">
        Rejected
      </span>
    );
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">User Management</h1>
          <p className="text-muted-foreground mt-1">Create, update, and manage access privileges for Adani HR NDC admins</p>
        </div>
      </div>

      {/* Card Container */}
      <div className="bg-card rounded-[4px] border border-border flex flex-col overflow-hidden">
        {/* Table Controls */}
        <div className="p-4 border-b border-border bg-muted/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 w-full border border-border rounded-[4px] bg-input-background focus:outline-none focus:ring-1 focus:ring-primary text-sm placeholder:text-muted-foreground"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={fetchUsers}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 border border-border bg-card hover:bg-muted text-foreground text-sm font-medium rounded-[4px] transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-muted-foreground ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button
              onClick={() => { resetForm(); setIsAddOpen(true); }}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-[4px] transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </div>
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">User Details</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Created Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground tracking-wide">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Loader2 className="w-8 h-8 animate-spin text-primary" />
                      <span>Loading users...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-16 text-center text-muted-foreground">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Info className="w-10 h-10 text-muted-foreground/50" />
                      <span className="font-medium text-base">No users found</span>
                      <span className="text-sm text-muted-foreground max-w-xs leading-relaxed">
                        {searchTerm ? "Try adjusting your search criteria" : "Click 'Add User' to create the first user"}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                paginatedUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-foreground">{user.name || "Unnamed"}</span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <Mail className="w-3.5 h-3.5 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">{user.email}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">{getRoleBadge(user.role)}</td>
                    <td className="px-4 py-2.5">{getStatusBadge(user.status)}</td>
                    <td className="px-4 py-2.5 text-sm text-muted-foreground whitespace-nowrap">
                      {formatDate(user.requested_at)}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => openEdit(user)}
                          className="p-1.5 rounded-[4px] bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
                          title="Edit User"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setUserToDelete(user.email)}
                          className="p-1.5 rounded-[4px] bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                          title="Delete User"
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

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border flex flex-wrap items-center justify-between gap-4 bg-card">
          <div className="flex flex-wrap items-center gap-4">
            <div className="text-sm text-muted-foreground">
              Showing {filteredUsers.length > 0 ? startIndex + 1 : 0} to {Math.min(startIndex + itemsPerPage, filteredUsers.length)} of {filteredUsers.length} records
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
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground bg-card"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-foreground">
              Page {currentPage} of {totalPages || 1}
            </span>
            <button
              onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages || totalPages === 0}
              className="p-2 rounded-[4px] border border-border hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed text-foreground bg-card"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Add User Modal */}
      <Dialog open={isAddOpen} onOpenChange={(open) => !isSubmitting && setIsAddOpen(open)}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Add New User</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddSubmit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Employee Name"
                className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Email Address <span className="text-red-500">*</span></label>
              <div className="relative">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="username@adani.com"
                  className="w-full pl-9 pr-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                  disabled={isSubmitting}
                />
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Password <span className="text-red-500">*</span></label>
              <div className="relative">
                <input
                  type={showAddPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={showAddPassword ? "Type user password" : "••••••••"}
                  className="w-full pl-9 pr-10 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                  disabled={isSubmitting}
                />
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <button
                  type="button"
                  onClick={() => setShowAddPassword(!showAddPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none cursor-pointer"
                  title={showAddPassword ? "Hide password" : "Show password"}
                >
                  {showAddPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as any)}
                className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="admin">Admin</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Save User
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit User Modal */}
      <Dialog open={isEditOpen} onOpenChange={(open) => !isSubmitting && setIsEditOpen(open)}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Edit User Access</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Name <span className="text-red-500">*</span></label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Employee Name"
                className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Email Address</label>
              <div className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-muted text-muted-foreground flex items-center gap-2">
                <Mail className="w-4 h-4" />
                {email}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Password <span className="text-xs text-muted-foreground">(Leave blank to keep current)</span></label>
              <div className="relative">
                <input
                  type={showEditPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={showEditPassword ? "Type new password to update" : "••••••••"}
                  className="w-full pl-9 pr-10 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
                  disabled={isSubmitting}
                />
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <button
                  type="button"
                  onClick={() => setShowEditPassword(!showEditPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none cursor-pointer"
                  title={showEditPassword ? "Hide password" : "Show password"}
                >
                  {showEditPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {showEditPassword && !password && (
                <p className="text-xs text-muted-foreground italic mt-1">
                  Existing passwords are securely encrypted in the database. Type a new password above to update it.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as any)}
                className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="admin">Admin</option>
                <option value="super_admin">Super Admin</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as any)}
                className="w-full px-3 py-2 border border-border rounded-[4px] text-sm bg-input-background focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="approved">Approved</option>
                <option value="pending">Pending</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-border mt-6">
              <button
                type="button"
                onClick={() => setIsEditOpen(false)}
                className="px-4 py-2 border border-border text-foreground hover:bg-muted text-sm font-medium rounded-[4px] transition-colors"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 text-sm font-medium rounded-[4px] transition-colors flex items-center gap-2"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Save Changes
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={userToDelete !== null} onOpenChange={(open) => !open && setUserToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{userToDelete}</strong>? This action cannot be undone and the user will lose access to the system.
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
