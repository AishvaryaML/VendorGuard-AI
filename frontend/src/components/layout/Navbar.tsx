import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../../services/api';
import { Menu, Search, Bell, Shield, User, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';

interface NavbarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ sidebarOpen, setSidebarOpen }) => {
  const { data: health, isLoading, isError, refetch } = useQuery({
    queryKey: ['system-health'],
    queryFn: healthApi.checkHealth,
    refetchInterval: 30000, // Refresh every 30s
  });

  return (
    <header className="h-16 bg-[#0D121F]/90 backdrop-blur-md border-b border-border sticky top-0 z-30 px-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          title="Toggle Navigation Sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Bar */}
        <div className="relative hidden sm:block w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search vendors, policies, or domain risk..."
            className="w-full pl-9 pr-4 py-1.5 bg-slate-900/80 border border-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyber-cyan transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Backend API Health Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface border border-border text-xs">
          <span className="text-slate-400 hidden md:inline">API Engine:</span>
          {isLoading ? (
            <span className="flex items-center gap-1.5 text-slate-400">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyber-cyan" />
              Connecting...
            </span>
          ) : isError ? (
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 text-rose-400 font-medium hover:underline"
              title="Click to retry health check"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              Offline
            </button>
          ) : (
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              {health?.status === 'healthy' ? 'Healthy' : 'Degraded'}
            </span>
          )}
        </div>

        {/* Alerts Bell Button */}
        <button className="relative p-2 text-slate-400 hover:text-white hover:bg-slate-800/60 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyber-cyan ring-4 ring-[#0D121F]"></span>
        </button>

        {/* User Profile Menu */}
        <div className="flex items-center gap-3 pl-3 border-l border-border">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyber-blue to-cyber-purple flex items-center justify-center text-white text-xs font-bold">
            AV
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-white">Risk Analyst</div>
            <div className="text-[10px] text-slate-400">Enterprise Admin</div>
          </div>
        </div>
      </div>
    </header>
  );
};
