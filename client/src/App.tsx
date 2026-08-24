import { createBrowserRouter, RouterProvider, Navigate, Outlet } from "react-router";
import { Overview } from "./features/overview/Overview";
import { Analytics } from "./features/analytics/Analytics";
import { FNFManagement } from "./features/fnf/FNFManagement";
import { EmailConfig } from "./features/email-config/EmailConfig";
import { RMEmailConfigurationPage } from "./features/rm-email-configuration/RMEmailConfigurationPage";
import { EmployeeEmailMasterPage } from "./features/employee-email-master/EmployeeEmailMasterPage";
import { Sidebar } from "./layouts/Sidebar";
import { SidebarProvider, useSidebar } from "./context/SidebarContext";
import { Toaster } from "sonner";
import { RouteErrorFallback } from "./components/common/RouteErrorFallback";
import { GlobalErrorBoundary } from "./components/common/GlobalErrorBoundary";

// Auth context and routes
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/common/ProtectedRoute";
import { PendingApproval } from "./features/auth/PendingApproval";
import { AccessDenied } from "./features/auth/AccessDenied";
import { Login } from "./features/auth/Login";
import { ResetPassword } from "./features/auth/ResetPassword";
import { UserManagement } from "./features/user-management/UserManagement";

function Layout() {
  const { isCollapsed } = useSidebar();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={`transition-all duration-300 ${isCollapsed ? "ml-20" : "ml-64"}`}
      >
        <Outlet />
      </div>
      <Toaster position="bottom-right" richColors />
    </div>
  );
}

const router = createBrowserRouter(
  [
    {
      errorElement: <RouteErrorFallback />,
      children: [
        {
          path: "/pending",
          element: <PendingApproval />,
        },
        {
          path: "/access-denied",
          element: <AccessDenied />,
        },
        {
          path: "/login",
          element: <Login />,
        },
        {
          path: "/reset-password",
          element: <ResetPassword />,
        },
        {
          element: (
            <ProtectedRoute>
              <SidebarProvider>
                <Layout />
              </SidebarProvider>
            </ProtectedRoute>
          ),
          children: [
            { index: true, element: <Navigate to="ndc-reporting/overview" replace /> },
            { path: "ndc-reporting/overview", element: <Overview /> },
            { path: "ndc-reporting/analytics", element: <Analytics /> },
            { path: "ndc-reporting/fnf", element: <FNFManagement /> },
            { path: "ndc-reporting/email-config", element: <EmailConfig /> },
            { path: "ndc-reporting/rm-email-configuration", element: <RMEmailConfigurationPage /> },
            { path: "ndc-reporting/employee-email-master", element: <EmployeeEmailMasterPage /> },
            { path: "ndc-reporting/user-management", element: <UserManagement /> },
          ],
        },
      ],
    },
  ],
  { basename: import.meta.env.BASE_URL }
);

export default function App() {
  return (
    <GlobalErrorBoundary>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </GlobalErrorBoundary>
  );
}
