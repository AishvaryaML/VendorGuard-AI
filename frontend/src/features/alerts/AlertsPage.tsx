import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Bell, CheckCheck, Filter } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Security & Policy Change Alerts"
        description="Real-time notifications for policy modifications, risk score drops, and news/threat events."
        action={
          <button className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border text-slate-300 hover:text-white font-medium text-xs rounded-lg">
            <CheckCheck className="w-3.5 h-3.5" /> Mark All as Read
          </button>
        }
      />

      <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-4">
          <Bell className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white">Alert Dispatch Hub Ready</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          When continuous monitoring detects policy text diffs or risk score elevation, event alerts will stream directly to this feed.
        </p>
      </div>
    </div>
  );
};
