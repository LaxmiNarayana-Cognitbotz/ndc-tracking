import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import api from "../lib/axios";

export interface User {
  email: string;
  name: string;
  role: "super_admin" | "admin";
  status: "approved" | "pending" | "rejected";
}

interface AuthContextType {
  user: User | null;
  ssoEnabled: boolean;
  isSuperAdmin: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: () => Promise<void>;
  loginWithPassword: (email: string, password: string) => Promise<any>;
  verifyOtp: (email: string, otpCode: string) => Promise<any>;
  resendOtp: (email: string) => Promise<any>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ssoEnabled, setSsoEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Check login parameters from URL (OIDC Callback redirect)
  const checkUrlParams = () => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const email = params.get("email");
    const role = params.get("role") as User["role"];
    const name = params.get("name");

    if (token && email && role) {
      localStorage.setItem("token", token);
      const newUser: User = {
        email,
        name: name || email.split("@")[0],
        role,
        status: "approved",
      };
      setUser(newUser);
      
      // Clean up URL parameters from browser address bar
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
      return true;
    }
    return false;
  };

  const loadAuth = async () => {
    try {
      setSsoEnabled(false);

      const token = localStorage.getItem("token");
      if (token) {
        try {
          const profileRes = await api.get<any>("api/auth/me", {
            skipGlobalToast: true,
          } as any);
          const profileData = profileRes.data?.data || profileRes.data;
          setUser(profileData);
        } catch (err: any) {
          console.error("Profile fetch failed, logging out", err);
          localStorage.removeItem("token");
          setUser(null);
        }
      } else {
        setUser(null);
      }
    } catch (err) {
      console.error("Failed to load auth profile", err);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkUrlParams();
    loadAuth();
  }, []);

  const login = async () => {
    // Left as legacy/no-op
  };

  const loginWithPassword = async (email: string, password: string) => {
    const res = await api.post<any>("api/auth/login", { email, password });
    const data = res.data?.data || res.data;
    if (data.token) {
      localStorage.setItem("token", data.token);
      setUser({
        email: data.email,
        name: data.name,
        role: data.role,
        status: data.status,
      });
    }
    return data;
  };

  const verifyOtp = async (email: string, otpCode: string) => {
    const res = await api.post<any>("api/auth/verify-otp", { email, otp_code: otpCode });
    const data = res.data?.data || res.data;
    if (data.token) {
      localStorage.setItem("token", data.token);
      setUser({
        email: data.email,
        name: data.name,
        role: data.role,
        status: data.status,
      });
    }
    return data;
  };

  const resendOtp = async (email: string) => {
    const res = await api.post<any>("api/auth/resend-otp", { email });
    return res.data?.data || res.data;
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      try {
        await api.post<any>("api/auth/logout");
      } catch (err) {
        console.error("Logout request to backend failed", err);
      }
    } finally {
      localStorage.removeItem("token");
      setUser(null);
      setIsLoading(false);
    }
  };

  const isSuperAdmin = user?.role === "super_admin";
  const isAdmin = user?.role === "admin" || user?.role === "super_admin";

  return (
    <AuthContext.Provider
      value={{
        user,
        ssoEnabled,
        isSuperAdmin,
        isAdmin,
        isLoading,
        login,
        loginWithPassword,
        verifyOtp,
        resendOtp,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
