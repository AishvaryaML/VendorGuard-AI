import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldAlert,
  LayoutDashboard,
  Building2,
  Activity,
  BarChart3,
  Clock,
  ShieldCheck,
  Bell,
  FileText,
  Bot,
  Settings,
  ChevronRight
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen }) => {
  const navItems = [
    { name: 'Executive Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Vendor Directory', path: '/vendors', icon: Building2 },
    { name: 'Continuous Monitoring', path: '/monitoring', icon: Activity },
    { name: 'Risk Analytics', path: '/risk-analytics', icon: BarChart3 },
    { name: 'Timeline & History', path: '/timeline', icon: Clock },
    { name: 'Compliance Intelligence', path: '/compliance', icon: ShieldCheck },
    { name: 'Alerts Center', path: '/alerts', icon: Bell },
    { name: 'Executive Reports', path: '/reports', icon: FileText },
    { name: 'AI Risk Assistant', path: '/assistant', icon: Bot },
    { name: 'System Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 z-40 h-screen transition-all duration-300 ${
        isOpen ? 'w-64' : 'w-20'
      } bg-[#0D121F] border-r border-border flex flex-col justify-between`}
    >
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center px-4 border-b border-border bg-[#090D17]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-cyan to-cyber-blue p-0.5 shadow-cyber-glow flex items-center justify-center">
              <div className="w-full h-full bg-[#0B0F17] rounded-[10px] flex items-center justify-center">
                <ShieldAlert className="w-5 h-5 text-cyber-cyan" />
              </div>
            </div>
            {isOpen && (
              <div>
                <span className="font-bold text-base tracking-wider text-white bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-300">
                  VendorGuard
                </span>
                <span className="text-xs font-semibold text-cyber-cyan ml-1 px-1.5 py-0.5 rounded bg-cyber-cyan/10 border border-cyber-cyan/30">
                  AI
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                    isActive
                      ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30 shadow-cyber-glow'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="w-5 h-5 shrink-0 transition-transform group-hover:scale-110" />
                {isOpen && <span className="truncate">{item.name}</span>}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      {isOpen && (
        <div className="p-4 m-3 rounded-xl bg-surface/80 border border-border">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Continuous Scanner</span>
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Active
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div className="bg-cyber-cyan h-1.5 rounded-full w-3/4 animate-pulse"></div>
          </div>
        </div>
      )}
    </aside>
  );
};
