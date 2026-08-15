import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { FileText, Download, Printer } from 'lucide-react';

export const ReportsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Risk & Audit Reports"
        description="Generate evidence-backed PDF executive vendor risk summaries, compliance exports, and audit logs."
        action={
          <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-semibold text-xs rounded-lg">
            <Download className="w-4 h-4" /> Export Executive Summary
          </button>
        }
      />

      <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
        <div className="w-16 h-16 rounded-2xl bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan mb-4">
          <FileText className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white">Executive Report Generator Ready</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          ReportLab PDF generation APIs will create downloadable executive risk briefs and audit logs in Phase 6.
        </p>
      </div>
    </div>
  );
};
