import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Clock, History, GitCompare } from 'lucide-react';

export const TimelinePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Temporal Policy & Risk Timeline"
        description="Historical risk trajectory analysis, document version comparison, and semantic change diffs."
      />

      <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
        <div className="w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-4">
          <History className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white">Temporal Risk Timeline Ready</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          Historical risk score snapshots (`vendor_risk_snapshots`) and SHA-256 semantic diff visualizations will render here.
        </p>
      </div>
    </div>
  );
};
