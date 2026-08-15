import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Activity, Play, RefreshCw, Clock } from 'lucide-react';

export const MonitoringPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Continuous Monitoring Engine"
        description="Automated background schedule monitoring, SHA-256 policy change verification, and delta risk recalculation."
        action={
          <button className="flex items-center gap-2 px-4 py-2 bg-surface border border-cyber-cyan/40 text-cyber-cyan font-semibold text-xs rounded-lg hover:bg-cyber-cyan/10 transition-colors">
            <Play className="w-4 h-4" /> Trigger Immediate Monitor Cycle
          </button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Active Scheduler Status</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">APScheduler Ready</div>
          <p className="text-xs text-slate-500 mt-1">Python background scheduler configured</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Monitoring Frequencies</span>
            <Clock className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">Daily / Weekly</div>
          <p className="text-xs text-slate-500 mt-1">Configurable per vendor profile</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Last Global Check</span>
            <RefreshCw className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">System Idle</div>
          <p className="text-xs text-slate-500 mt-1">Awaiting vendor setup</p>
        </div>
      </div>

      <div className="glass-panel rounded-xl border border-border p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
        <Activity className="w-12 h-12 text-cyber-cyan mb-4 animate-pulse" />
        <h3 className="text-xl font-bold text-white">Continuous Monitoring Architecture Operational</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          Scheduled monitoring routines will execute automated policy recrawls and trigger delta risk calculations when active vendors are added.
        </p>
      </div>
    </div>
  );
};
