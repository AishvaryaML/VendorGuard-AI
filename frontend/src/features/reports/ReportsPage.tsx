import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import { FileText, Download, Printer, Building2, ShieldAlert, Loader2 } from 'lucide-react';
import { vendorApi } from '../../services/api';
import { Vendor } from '../../types';

export const ReportsPage: React.FC = () => {
  const { data: vendors = [], isLoading } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Risk & Audit Reports"
        description="Generate evidence-backed PDF executive vendor risk summaries, compliance exports, and audit logs."
        action={
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-semibold text-xs rounded-lg hover:opacity-90 transition-opacity"
          >
            <Printer className="w-4 h-4" /> Print / Export Executive Summary
          </button>
        }
      />

      {isLoading ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-cyber-cyan animate-spin mb-3" />
          <p className="text-sm text-slate-400">Compiling executive vendor reports...</p>
        </div>
      ) : vendors.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <FileText className="w-12 h-12 text-cyber-cyan mb-4" />
          <h3 className="text-xl font-bold text-white">Executive Report Engine Ready</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Register vendors and run policy assessments to generate downloadable executive risk briefs.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-border pb-3">
              <FileText className="w-5 h-5 text-cyber-cyan" /> Registered Vendor Audit Briefs ({vendors.length})
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {vendors.map((v) => (
                <div key={v.id} className="p-4 rounded-xl bg-slate-900/90 border border-border space-y-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-white text-sm flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-cyber-cyan" /> {v.name}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full border text-[10px] font-bold bg-surface text-cyber-cyan border-cyber-cyan/30">
                      {v.risk_tier} Risk
                    </span>
                  </div>
                  <div className="text-slate-400 font-mono">{v.domain}</div>
                  <div className="text-slate-300 font-semibold">
                    Overall Risk Score: <span className={v.current_risk_score >= 50 ? 'text-rose-400' : 'text-emerald-400'}>{v.current_risk_score.toFixed(1)} / 100</span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Monitoring: {v.monitoring_frequency} | Status: {v.status}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
