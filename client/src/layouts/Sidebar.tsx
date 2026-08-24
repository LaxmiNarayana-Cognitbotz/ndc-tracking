import { Link, useLocation } from "react-router";
import { LayoutDashboard, BarChart3, ChevronLeft, ChevronRight, FileText, Mail, Settings, Users, LogOut, Contact } from "lucide-react";
import imgLogo from "../assets/images/image.png";
import { useSidebar } from "../context/SidebarContext";
import { useAuth } from "../context/AuthContext";

export function Sidebar() {
  const location = useLocation();
  const { isCollapsed, toggleSidebar } = useSidebar();
  const { user, logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  const getInitials = () => {
    if (!user) return "?";
    const name = user.name || "";
    const email = user.email || "";
    if (name) {
      const parts = name.trim().split(/[.\s_-]+/);
      const first = parts[0]?.charAt(0) || "";
      const second = parts[1]?.charAt(0) || "";
      if (first && second) return (first + second).toUpperCase();
      return first.toUpperCase();
    }
    return email.charAt(0).toUpperCase();
  };

  const menuItems = [
    {
      path: "/ndc-reporting/overview",
      label: "Overview Dashboard",
      icon: LayoutDashboard,
    },
    {
      path: "/ndc-reporting/analytics",
      label: "Analytics Dashboard",
      icon: BarChart3,
    },
    {
      path: "/ndc-reporting/fnf",
      label: "F&F Management",
      icon: FileText,
    },
    {
      path: "/ndc-reporting/email-config",
      label: "Email Recipients",
      icon: Mail,
    },
    {
      path: "/ndc-reporting/rm-email-configuration",
      label: "RM Email Master",
      icon: Settings,
    },
    {
      path: "/ndc-reporting/employee-email-master",
      label: "Employee Email Master",
      icon: Contact,
    },
  ];



  return (
    <div
      className={`h-screen bg-sidebar border-r border-sidebar-border flex flex-col fixed left-0 top-0 z-30 transition-all duration-300 ${
        isCollapsed ? "w-20" : "w-64"
      }`}
    >
      <div className={`py-5 border-b border-sidebar-border flex items-center ${isCollapsed ? "justify-center px-3" : "justify-between px-5"}`}>
        {!isCollapsed && (
          <div className="flex items-center gap-3">
            <img src={imgLogo} alt="Adani" className="h-9 w-auto object-contain" />
            <div className="h-6 w-px bg-sidebar-border shrink-0" />
            <span className="text-[15px] font-bold tracking-wide text-sidebar-foreground/90 whitespace-nowrap">
              HR NDC System
            </span>
          </div>
        )}
        {isCollapsed && (
          <img src={imgLogo} alt="Adani" className="w-12 h-auto object-contain" />
        )}
      </div>

      <div className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto no-scrollbar">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                active
                  ? "bg-gradient-to-r from-[#003b70] to-[#1e5a8e] text-white shadow-md shadow-[#003b70]/10 font-bold"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              } ${isCollapsed ? "justify-center" : ""}`}
              title={isCollapsed ? item.label : ""}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!isCollapsed && <span className="font-semibold text-sm whitespace-nowrap">{item.label}</span>}
            </Link>
          );
        })}
      </div>

      {user?.role === "super_admin" && (
        <div className="shrink-0">
          <div className="h-px bg-sidebar-border" />
          <div className="px-3 py-2">
            <Link
              to="/ndc-reporting/user-management"
              className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-all duration-200 ${
                isActive("/ndc-reporting/user-management")
                  ? "bg-gradient-to-r from-[#003b70] to-[#1e5a8e] text-white shadow-md shadow-[#003b70]/10"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              } ${isCollapsed ? "justify-center" : ""}`}
              title={isCollapsed ? "User Management" : ""}
            >
              <Users className="w-4 h-4 flex-shrink-0" />
              {!isCollapsed && <span className="font-medium text-xs whitespace-nowrap">User Management</span>}
            </Link>
          </div>
        </div>
      )}

      {user && !isCollapsed && (
        <div className="p-3 border-t border-sidebar-border bg-sidebar-accent/5">
          <div className="flex items-center justify-between gap-2 p-2 rounded-lg hover:bg-sidebar-accent/30 transition-colors">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#003b70] to-[#1e5a8e] text-white flex items-center justify-center font-bold text-xs shadow-sm uppercase shrink-0">
                {getInitials()}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] font-semibold text-sidebar-foreground truncate" title={user.name}>
                  {user.name}
                </span>
                <span className="text-[10px] text-sidebar-foreground/50 truncate mb-1" title={user.email}>
                  {user.email}
                </span>
                <div className="flex">
                  {user.role === "super_admin" ? (
                    <span className="px-1.5 py-0.5 rounded-[4px] text-[8px] font-bold bg-teal-500/10 text-teal-700 border border-teal-500/20 shrink-0 uppercase tracking-wider">
                      Super Admin
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded-[4px] text-[8px] font-bold bg-blue-500/10 text-blue-700 border border-blue-500/20 shrink-0 uppercase tracking-wider">
                      Admin
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={logout}
              className="p-1.5 rounded-md text-sidebar-foreground/40 hover:text-rose-600 hover:bg-rose-50 transition-all cursor-pointer shrink-0"
              title="Sign Out"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      )}

      {user && isCollapsed && (
        <div className="p-3 border-t border-sidebar-border flex flex-col items-center gap-3 bg-sidebar-accent/5">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#003b70] to-[#1e5a8e] text-white flex items-center justify-center font-bold text-xs shadow-sm uppercase" title={`${user.name} (${user.role})`}>
            {getInitials()}
          </div>
          <button
            onClick={logout}
            className="p-1.5 rounded-md text-sidebar-foreground/40 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
            title="Sign Out"
          >
            <LogOut size={16} />
          </button>
        </div>
      )}

      {/* Absolute Circular Collapse Toggle Button on Right Edge */}
      <button
        onClick={toggleSidebar}
        className="absolute top-20 -right-3.5 z-50 flex items-center justify-center w-7 h-7 rounded-full bg-white border border-slate-200 shadow-md hover:bg-slate-50 hover:border-slate-300 text-slate-500 hover:text-slate-700 active:scale-[0.9] transition-all cursor-pointer"
        title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
      >
        {isCollapsed ? (
          <ChevronRight className="w-4 h-4 stroke-[3]" />
        ) : (
          <ChevronLeft className="w-4 h-4 stroke-[3]" />
        )}
      </button>
    </div>
  );
}
