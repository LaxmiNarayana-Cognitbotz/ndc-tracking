import { useState, useEffect, FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { useAuth } from "../../context/AuthContext";
import { Eye, EyeOff, Loader2, Mail, Lock, CheckCircle2, ArrowLeft, KeyRound } from "lucide-react";
import imgLogo from "../../assets/images/image.png";
import api from "../../lib/axios";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from "../../components/ui/dialog";

export function Login() {
  const { user, loginWithPassword, verifyOtp, resendOtp } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // OTP Verification state
  const [step, setStep] = useState<"credentials" | "otp">("credentials");
  const [otpCode, setOtpCode] = useState("");
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [isResendingOtp, setIsResendingOtp] = useState(false);
  const [resendTimer, setResendTimer] = useState(0);

  // Forgot password modal states
  const [isForgotOpen, setIsForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isForgotSubmitting, setIsForgotSubmitting] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError, setForgotError] = useState("");

  useEffect(() => {
    let interval: any;
    if (resendTimer > 0) {
      interval = setInterval(() => {
        setResendTimer((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [resendTimer]);

  // If already authenticated, redirect to dashboard
  if (user && user.status === "approved") {
    return <Navigate to="/ndc-reporting/overview" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();

    if (!password) {
      setError("Password is required.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await loginWithPassword(cleanEmail, password);
      if (res?.requires_otp) {
        setStep("otp");
        setResendTimer(60);
        setOtpCode("");
        toast.success("Verification code sent to your email!");
      } else {
        navigate("/ndc-reporting/overview", { replace: true });
      }
    } catch (err: any) {
      console.error("Login failed:", err);
      setError(err.response?.data?.message || err.response?.data?.detail || "Invalid email or password.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOtpSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanOtp = otpCode.trim();
    if (cleanOtp.length !== 6) {
      setError("Please enter a valid 6-digit OTP.");
      return;
    }

    setIsVerifyingOtp(true);
    try {
      await verifyOtp(email.trim(), cleanOtp);
      toast.success("Login successful!");
      navigate("/ndc-reporting/overview", { replace: true });
    } catch (err: any) {
      console.error("OTP Verification failed:", err);
      setError(err.response?.data?.message || err.response?.data?.detail || "Invalid OTP code.");
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendTimer > 0 || isResendingOtp) return;
    setError(null);
    setIsResendingOtp(true);
    try {
      await resendOtp(email.trim());
      setResendTimer(60);
      toast.success("A new verification code has been sent to your email.");
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail || "Failed to resend OTP.");
    } finally {
      setIsResendingOtp(false);
    }
  };

  const handleForgotSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setForgotError("");
    const cleanEmail = forgotEmail.trim().toLowerCase();
    // if (!cleanEmail.endsWith("@adani.com")) {
    //   setForgotError("Email must end with @adani.com");
    //   return;
    // }

    setIsForgotSubmitting(true);
    try {
      const res = await api.post<any>("api/auth/forgot-password", { email: cleanEmail });
      setForgotSuccess(true);
      toast.success(res.data?.message || "Reset link sent!");
    } catch (err: any) {
      setForgotError(
        err.response?.data?.message || err.response?.data?.detail || "Failed to request password reset."
      );
    } finally {
      setIsForgotSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-slate-50">
      {/* Left side - Product Showcase (Visible on lg and up) */}
      <div className="hidden lg:flex lg:w-[55%] bg-gradient-to-br from-[#0b2e59] to-[#003b70] relative overflow-hidden flex-col justify-between p-12 text-white">
        {/* Subtle grid pattern overlay */}
        <div 
          className="absolute inset-0 opacity-[0.03] pointer-events-none" 
          style={{ 
            backgroundImage: "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
            backgroundSize: "24px 24px" 
          }} 
        />
        {/* Soft light reflection */}
        <div className="absolute top-[-20%] left-[-20%] w-[80%] h-[80%] rounded-full bg-blue-400/10 filter blur-[120px]" />

        {/* Brand header */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-white shadow-md">
            <img src={imgLogo} alt="Adani Logo" className="h-6 w-auto object-contain" />
          </div>
          <div className="h-4 w-px bg-white/20" />
          <span className="text-sm font-bold tracking-wider text-blue-200">HR NDC System</span>
        </div>

        {/* Value proposition content */}
        <div className="relative z-10 my-auto max-w-md space-y-6">
          <div className="space-y-3">
            <span className="inline-flex px-2.5 py-1 rounded-full text-xs font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Clearance & Tracking
            </span>
            <h1 className="text-4xl font-extrabold tracking-tight leading-tight">
              Manage Employee NDC Process Safely.
            </h1>
            <p className="text-sm text-blue-200/80 leading-relaxed font-medium">
              A comprehensive system for tracking department-wise No Demand Certificate approvals, managing outstanding items, and streamlining the employee exit workflow.
            </p>
          </div>

          {/* Interactive CSS Graphic: Clearance Status Card */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5 shadow-2xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#10b981] animate-pulse" />
                <span className="text-xs font-bold tracking-wider uppercase text-blue-200">Clearance Status</span>
              </div>
              <span className="text-[10px] text-white/40">Real-time update</span>
            </div>
            
            <div className="space-y-3.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-white/80">Department Clearances</span>
                <span className="font-bold text-[#10b981]">8 / 8 Cleared</span>
              </div>
              <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden">
                <div className="bg-gradient-to-r from-teal-400 to-[#10b981] h-full w-[100%] rounded-full" />
              </div>
              
              <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-white/5 text-[11px]">
                <div className="flex items-center gap-1.5 text-white/70">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                  <span>HR Dept: <strong className="text-white">Done</strong></span>
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                  <span>Finance: <strong className="text-white">Done</strong></span>
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                  <span>IT Assets: <strong className="text-white">Done</strong></span>
                </div>
                <div className="flex items-center gap-1.5 text-white/70">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/30" />
                  <span>Admin: <strong className="text-white">Done</strong></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-10 text-xs text-blue-200/50">
          © {new Date().getFullYear()} Adani Group. All rights reserved.
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="w-full lg:w-[45%] flex flex-col justify-between p-8 md:p-12 lg:p-16 bg-white">
        {/* Mobile Header (Visible only on mobile/tablet) */}
        <div className="lg:hidden flex items-center justify-between mb-8">
          <img src={imgLogo} alt="Adani Logo" className="h-7 w-auto object-contain" />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">HR NDC</span>
        </div>

        {/* Centered Login Card */}
        <div className="my-auto mx-auto w-full max-w-[360px] space-y-6">
          {step === "credentials" ? (
            <>
              <div className="space-y-1.5">
                <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  Sign In
                </h2>
                <p className="text-xs text-slate-500 font-medium">
                  Welcome back! Please enter your @adani.com credentials.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="p-3 text-[11px] font-semibold text-rose-600 bg-rose-50 rounded-lg border border-rose-100">
                    {error}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Email Address
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                      <Mail size={16} />
                    </span>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@adani.com"
                      className="w-full h-10 pl-10 pr-4 text-sm bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-400 font-medium"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setForgotEmail(email);
                        setForgotError("");
                        setForgotSuccess(false);
                        setIsForgotOpen(true);
                      }}
                      className="text-[11px] font-semibold text-[#003b70] hover:underline cursor-pointer"
                    >
                      Forgot Password?
                    </button>
                  </div>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                      <Lock size={16} />
                    </span>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full h-10 pl-10 pr-10 text-sm bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-400 font-medium"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-10 mt-2 flex items-center justify-center text-sm font-bold text-white rounded-lg bg-[#003b70] hover:bg-[#002f5a] shadow-sm hover:shadow transition-all cursor-pointer disabled:opacity-75 disabled:pointer-events-none"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    "Sign In"
                  )}
                </button>
              </form>
            </>
          ) : (
            <>
              <div className="space-y-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setStep("credentials");
                    setError(null);
                    setOtpCode("");
                  }}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-[#003b70] mb-2 transition-colors cursor-pointer"
                >
                  <ArrowLeft size={14} />
                  Back to Sign In
                </button>
                <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  Enter Verification Code
                </h2>
                <p className="text-xs text-slate-500 font-medium leading-relaxed">
                  We've sent a 6-digit OTP to <strong className="text-slate-800">{email}</strong>.
                </p>
              </div>

              <form onSubmit={handleVerifyOtpSubmit} className="space-y-4">
                {error && (
                  <div className="p-3 text-[11px] font-semibold text-rose-600 bg-rose-50 rounded-lg border border-rose-100">
                    {error}
                  </div>
                )}

                <div className="space-y-1">
                  <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    One-Time Password (OTP)
                  </label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                      <KeyRound size={16} />
                    </span>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="w-full h-11 pl-10 pr-4 text-center tracking-[0.35em] text-lg font-bold font-mono bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-300"
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isVerifyingOtp || otpCode.trim().length !== 6}
                  className="w-full h-10 mt-2 flex items-center justify-center text-sm font-bold text-white rounded-lg bg-[#003b70] hover:bg-[#002f5a] shadow-sm hover:shadow transition-all cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
                >
                  {isVerifyingOtp ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    "Verify & Sign In"
                  )}
                </button>

                <div className="pt-2 text-center text-xs text-slate-500">
                  Didn't receive code?{" "}
                  {resendTimer > 0 ? (
                    <span className="font-semibold text-slate-700">Resend in {resendTimer}s</span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleResendOtp}
                      disabled={isResendingOtp}
                      className="font-bold text-[#003b70] hover:underline cursor-pointer inline-flex items-center gap-1 disabled:opacity-50"
                    >
                      {isResendingOtp && <Loader2 className="w-3 h-3 animate-spin" />}
                      Resend OTP
                    </button>
                  )}
                </div>
              </form>
            </>
          )}

          {/* Footer info */}
          <div className="pt-4 border-t border-slate-100 text-left text-[10px] text-slate-400 font-semibold tracking-wide uppercase">
            Adani Group HR Portal • exit clearance tracking
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      <Dialog open={isForgotOpen} onOpenChange={(open) => !isForgotSubmitting && setIsForgotOpen(open)}>
        <DialogContent className="max-w-md p-6">
          <DialogHeader>
            <DialogTitle className="text-[#003b70] text-xl font-bold">Reset Password</DialogTitle>
          </DialogHeader>
          {forgotSuccess ? (
            <div className="space-y-4 py-4 text-center">
              <div className="w-12 h-12 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">Check Your Email</h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                If an account exists for <span className="font-semibold text-slate-800">{forgotEmail}</span>, we have sent a password reset link to your email.
              </p>
              <button
                type="button"
                onClick={() => setIsForgotOpen(false)}
                className="w-full h-10 mt-2 bg-[#003b70] text-white text-sm font-bold rounded-lg hover:bg-[#002f5a] transition-colors"
              >
                Close & Return to Sign In
              </button>
            </div>
          ) : (
            <form onSubmit={handleForgotSubmit} className="space-y-4 pt-2">
              <p className="text-xs text-slate-500 leading-relaxed">
                Enter your registered <strong>@adani.com</strong> email address below and we will send you a password reset link.
              </p>

              {forgotError && (
                <div className="p-3 text-[11px] font-semibold text-rose-600 bg-rose-50 rounded-lg border border-rose-100">
                  {forgotError}
                </div>
              )}

              <div className="space-y-1">
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                    <Mail size={16} />
                  </span>
                  <input
                    type="email"
                    required
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    placeholder="name@adani.com"
                    className="w-full h-10 pl-10 pr-4 text-sm bg-slate-50/50 text-slate-800 rounded-lg border border-slate-200 focus:outline-none focus:border-[#003b70] focus:ring-1 focus:ring-[#003b70] focus:bg-white transition-all placeholder-slate-400 font-medium"
                    disabled={isForgotSubmitting}
                  />
                </div>
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t border-slate-100 mt-6">
                <button
                  type="button"
                  onClick={() => setIsForgotOpen(false)}
                  className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 text-sm font-medium rounded-lg transition-colors"
                  disabled={isForgotSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isForgotSubmitting}
                  className="px-4 py-2 bg-[#003b70] text-white hover:bg-[#002f5a] disabled:opacity-50 text-sm font-bold rounded-lg transition-colors flex items-center gap-2"
                >
                  {isForgotSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Send Reset Link
                </button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
