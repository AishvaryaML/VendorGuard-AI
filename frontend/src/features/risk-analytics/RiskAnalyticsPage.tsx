import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { BarChart3, ShieldCheck, Lock, Scale, FileText } from 'lucide-react';

export const RiskAnalyticsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Risk Analytics Engine"
        description="Explainable 4-category vendor risk scorecards: Privacy, Security, Compliance, and Legal."
      />

      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Privacy Risk</span>
            <Lock className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">-- / 100</div>
          <p className="text-xs text-slate-500 mt-1">Data sharing, retention, GDPR/CCPA</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Security Posture</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">-- / 100</div>
          <p className="text-xs text-slate-500 mt-1">Encryption, SOC2/ISO, incident response</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Compliance Risk</span>
            <FileText className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">-- / 100</div>
          <p className="text-xs text-slate-500 mt-1">Audit rights, certifications, regulatory</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Legal Risk</span>
            <Scale className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">-- / 100</div>
          <p className="text-xs text-slate-500 mt-1">Liability caps, indemnity, jurisdiction</p>
        </div>
      </div>

      <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
        <BarChart3 className="w-12 h-12 text-cyber-cyan mb-4" />
        <h3 className="text-xl font-bold text-white">AI Risk Scoring Pipeline Ready</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          LangChain / LLM risk evaluation algorithms will populate multi-criteria scorecards and citation evidence in Phase 4.
        </p>
      </div>
    </div>
  );
};
