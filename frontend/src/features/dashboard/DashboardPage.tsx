import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Building2, ShieldAlert, Activity, CheckCircle2, TrendingUp, AlertTriangle, Eye } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Security Dashboard"
        description="Continuous third-party vendor risk intelligence, real-time posture metrics, and policy change monitoring."
        badge="Live MVP"
      />

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Monitored Vendors</span>
            <Building2 className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">0</span>
            <span className="text-xs font-medium text-slate-400">Database Ready</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Active vendor profiles in database</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>High/Critical Risk</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">0</span>
            <span className="text-xs font-medium text-emerald-400 flex items-center">
              <TrendingUp className="w-3 h-3 mr-1" /> 0%
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Vendors exceeding risk threshold</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Continuous Monitoring</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">0</span>
            <span className="text-xs font-medium text-amber-400">Scheduled Engine</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Automated re-crawl tasks scheduled</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Discovered Policies</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">0</span>
            <span className="text-xs font-medium text-emerald-400">SHA-256 Hashed</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Tracked document versions</p>
        </div>
      </div>

      {/* Main Content Placeholder Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-panel p-6 rounded-xl border border-border flex flex-col justify-center items-center min-h-[300px] text-center">
          <div className="w-14 h-14 rounded-2xl bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan mb-4">
            <Activity className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-semibold text-white">Temporal Risk Trend Engine Ready</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Once vendors are added in Phase 2, this panel will stream real-time temporal risk trajectories and category scores directly from PostgreSQL.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-border flex flex-col justify-center items-center text-center min-h-[300px]">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-4">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-semibold text-white">Alert Feed Ready</h3>
          <p className="text-sm text-slate-400 mt-2">
            No active policy change or risk elevation alerts detected.
          </p>
        </div>
      </div>
    </div>
  );
};
