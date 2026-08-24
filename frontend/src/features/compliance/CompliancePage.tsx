import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import { ShieldCheck, Award, FileCheck, Building2, CheckCircle2, AlertTriangle, ExternalLink, Loader2 } from 'lucide-react';
import { vendorApi, riskApi } from '../../services/api';
import { Vendor, RiskAssessment } from '../../types';

export const CompliancePage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');

  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  const activeVendorId = selectedVendorId || (vendors.length > 0 ? vendors[0].id : '');

  const { data: assessment, isLoading: isLoadingAssessment } = useQuery<RiskAssessment>({
    queryKey: ['risk-assessment', activeVendorId],
    queryFn: () => riskApi.getRiskAssessment(activeVendorId),
    enabled: !!activeVendorId,
  });

  const compScoreObj = assessment?.category_scores?.find(
    (c) => c.category_name.toLowerCase() === 'compliance'
  );
  const compScore = compScoreObj ? compScoreObj.score : 0;
  const compFindings = (assessment?.key_findings || []).filter(
    (f) => f.category.toLowerCase() === 'compliance'
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance & Certification Intelligence"
        description="Regulatory framework mapping (SOC2, ISO27001, GDPR, HIPAA, CCPA) across third-party vendor base."
      />

      {/* Vendor Selector Header */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col sm:flex-row justify-between items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-white">Vendor Selection:</span>
        </div>
        <select
          value={activeVendorId}
          onChange={(e) => setSelectedVendorId(e.target.value)}
          disabled={vendors.length === 0}
          className="w-full sm:w-72 px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
        >
          {vendors.length === 0 ? (
            <option value="">No vendors registered</option>
          ) : (
            vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.domain})
              </option>
            ))
          )}
        </select>
      </div>

      {vendors.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <ShieldCheck className="w-12 h-12 text-emerald-400 mb-4" />
          <h3 className="text-xl font-bold text-white">Compliance Framework Ready</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Register vendors in the catalog to discover compliance documents and evaluate SOC2/ISO/GDPR compliance risk.
          </p>
        </div>
      ) : isLoadingAssessment ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mb-3" />
          <p className="text-sm text-slate-400">Loading compliance intelligence...</p>
        </div>
      ) : (
        <>
          {/* Compliance KPI Banner */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="glass-panel p-5 rounded-xl border border-border">
              <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
                <span>Compliance Risk Score</span>
                <Award className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-3xl font-extrabold text-white mt-2">{compScore.toFixed(1)} / 100</div>
              <p className="text-[11px] text-slate-500 mt-1">Audit rights & regulatory posture</p>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-border">
              <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
                <span>Compliance Findings</span>
                <FileCheck className="w-4 h-4 text-cyber-cyan" />
              </div>
              <div className="text-3xl font-extrabold text-white mt-2">{compFindings.length} Extracted</div>
              <p className="text-[11px] text-slate-500 mt-1">Grounded in stored policy documents</p>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-border">
              <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
                <span>Regulatory Standards</span>
                <ShieldCheck className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white mt-2">SOC2 / GDPR / DPA</div>
              <p className="text-[11px] text-slate-500 mt-1">Tracked via document classifier</p>
            </div>
          </div>

          {/* Compliance Findings List */}
          <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-border pb-3">
              <ShieldCheck className="w-5 h-5 text-emerald-400" /> Extracted Compliance Risk Findings
            </h3>

            {compFindings.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No high compliance risk findings identified for this vendor.
              </div>
            ) : (
              <div className="space-y-3">
                {compFindings.map((finding, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-900/90 border border-border space-y-2 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-white">{finding.finding}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        {finding.severity} Severity
                      </span>
                    </div>
                    {finding.evidence && (
                      <p className="text-slate-300 italic bg-surface p-2.5 rounded border-l-2 border-emerald-400">
                        "{finding.evidence}"
                      </p>
                    )}
                    {finding.recommendation && (
                      <p className="text-slate-400">
                        <strong className="text-cyber-cyan">Recommendation:</strong> {finding.recommendation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
