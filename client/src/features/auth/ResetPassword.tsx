import { useState, useEffect } from "react";
import { useSearchParams, useNavigate, Link } from "react-router";
import { Eye, EyeOff, Loader2, Lock, CheckCircle2, AlertCircle, ArrowLeft } from "lucide-react";
import api from "../../lib/axios";
import { toast } from "sonner";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [isValidating, setIsValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [tokenError, setTokenError] = useState("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!token) {
      setIsValidating(false);
      setTokenValid(false);
      setTokenError("Missing or invalid password reset token.");
      return;
    }

    const verifyToken = async () => {
      try {
        const res = await api.get<any>(`api/auth/verify-reset-token/${token}`);
        // API wraps response in { status, data, message } envelope
        const responseData = res.data?.data || res.data;
        if (responseData?.valid) {
          setTokenValid(true);
          setUserEmail(responseData.email || "");
        } else {
          setTokenValid(false);
          setTokenError("Password reset link is invalid or expired.");
        }
      } catch (err: any) {
        setTokenValid(false);
        setTokenError(
          err.response?.data?.message || err.response?.data?.detail || "Password reset link is invalid or has expired."
        );
      } finally {
        setIsValidating(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!newPassword.trim()) {
      setFormError("Please enter a new password.");
      return;
    }

    if (newPassword.length < 4) {
      setFormError("Password must be at least 4 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("api/auth/reset-password", {
        token,
        new_password: newPassword.trim(),
      });
      setIsSuccess(true);
      toast.success("Password reset successfully!");
      setTimeout(() => {
        navigate("/login");
      }, 2500);
    } catch (err: any) {
      setFormError(
        err.response?.data?.message || err.response?.data?.detail || "Failed to reset password. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-4">
      {/* Background Gradients */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-blue-600/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-tl from-[#003b70]/20 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-100 relative z-10 p-8">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-[#003b70]/10 text-[#003b70] rounded-xl mb-3">
            <Lock className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Set New Password</h1>
          <p className="text-xs text-slate-500 mt-1">Adani HR NDC Tracking Platform</p>
        </div>

        {/* Loading State */}
        {isValidating ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-500">
            <Loader2 className="w-8 h-8 animate-spin text-[#003b70]" />
            <span className="text-sm font-medium">Verifying reset link...</span>
          </div>
        ) : !tokenValid ? (
          /* Invalid Token State */
          <div className="space-y-6 text-center py-4">
            <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Invalid or Expired Link</h2>
              <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">{tokenError}</p>
            </div>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 w-full h-10 bg-[#003b70] hover:bg-[#002f5a] text-white text-sm font-bold rounded-lg transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Login
            </Link>
          </div>
        ) : isSuccess ? (
          /* Success State */
          <div className="space-y-6 text-center py-4">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800">Password Reset Successful!</h2>
              <p className="text-xs text-slate-500 mt-1">
                Your password has been updated. Redirecting you to login...
              </p>
            </div>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 w-full h-10 bg-[#003b70] text-white text-sm font-bold rounded-lg hover:bg-[#002f5a] transition-colors"
            >
              Proceed to Sign In
            </Link>
          </div>
        ) : (
          /* Password Reset Form */
          <form onSubmit={handleSubmit} className="space-y-4">
            {userEmail && (
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs text-slate-600">
                Resetting password for: <span className="font-semibold text-slate-800">{userEmail}</span>
              </div>
            )}

            {formError && (
              <div className="p-3 text-[11px] font-semibold text-rose-600 bg-rose-50 rounded-lg border border-rose-100">
                {formError}
              </div>
            )}

            {/* New Password */}
            <div className="space-y-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                New Password
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock size={16} />
                </span>
                <input
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder={showNewPassword ? "Type new password" : "••••••••"}
                  className="w-full h-10 pl-10 pr-10 text-sm bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-400 font-medium"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                  title={showNewPassword ? "Hide password" : "Show password"}
                >
                  {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div className="space-y-1">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Confirm New Password
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                  <Lock size={16} />
                </span>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder={showConfirmPassword ? "Confirm new password" : "••••••••"}
                  className="w-full h-10 pl-10 pr-10 text-sm bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-400 font-medium"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                  title={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-10 mt-2 flex items-center justify-center text-sm font-bold text-white rounded-lg bg-[#003b70] hover:bg-[#002f5a] shadow-sm hover:shadow transition-all cursor-pointer disabled:opacity-75 disabled:pointer-events-none"
            >
              {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : "Save New Password"}
            </button>

            <div className="text-center pt-2">
              <Link to="/login" className="text-xs font-semibold text-[#003b70] hover:underline inline-flex items-center gap-1">
                <ArrowLeft className="w-3 h-3" /> Back to Login
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
