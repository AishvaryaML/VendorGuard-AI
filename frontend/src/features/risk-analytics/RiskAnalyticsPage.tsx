import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  BarChart3,
  ShieldCheck,
  Lock,
  Scale,
  FileText,
  Building2,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Loader2,
  Sparkles,
  Quote,
  HelpCircle,
} from 'lucide-react';
import { vendorApi, riskApi } from '../../services/api';
import { Vendor, RiskAssessment, RiskTier } from '../../types';

export const RiskAnalyticsPage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');

  // Fetch Vendor Catalog
  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Auto-select first vendor when vendors list loads
  useEffect(() => {
    if (vendors.length > 0 && !selectedVendorId) {
      setSelectedVendorId(vendors[0].id);
    }
  }, [vendors, selectedVendorId]);

  // Fetch Risk Assessment for selected vendor
  const {
    data: assessment,
    isLoading: isLoadingAssessment,
    isError: isAssessmentError,
  } = useQuery<RiskAssessment>({
    queryKey: ['risk-assessment', selectedVendorId],
    queryFn: () => riskApi.getRiskAssessment(selectedVendorId),
    enabled: !!selectedVendorId,
    retry: 1,
  });

  const getTierBadge = (tier: RiskTier) => {
    switch (tier) {
      case 'Low':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'Medium':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'High':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'Critical':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
    }
  };

  const selectedVendor = vendors.find((v) => v.id === selectedVendorId);

  // Extract category scores helper
  const getCatScore = (catName: string): { score: number; justification?: string } => {
    if (!assessment || !assessment.category_scores) {
      return { score: 0, justification: 'No assessment generated yet.' };
    }
    const cat = assessment.category_scores.find(
      (c) => c.category_name.toLowerCase() === catName.toLowerCase()
    );
    return {
      score: cat ? cat.score : 0,
      justification: cat?.justification || 'No findings reported.',
    };
  };

  const privacyCat = getCatScore('Privacy');
  const securityCat = getCatScore('Security');
  const complianceCat = getCatScore('Compliance');
  const legalCat = getCatScore('Legal');

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Risk Analytics Engine"
        description="Explainable 4-category vendor risk scorecards: Privacy, Security, Compliance, and Legal."
      />

      {/* Vendor Selector Header Bar */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Building2 className="w-5 h-5 text-cyber-cyan" />
          <span className="text-xs font-semibold text-white">Select Vendor for Risk Analysis:</span>
        </div>
        <div className="w-full sm:w-80">
          <select
            value={selectedVendorId}
            onChange={(e) => setSelectedVendorId(e.target.value)}
            disabled={isLoadingVendors || vendors.length === 0}
            className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-cyber-cyan"
          >
            {vendors.length === 0 ? (
              <option value="">No registered vendors</option>
            ) : (
              vendors.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.domain}) — {v.risk_tier} Risk
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {!selectedVendorId || vendors.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <BarChart3 className="w-12 h-12 text-cyber-cyan mb-4" />
          <h3 className="text-xl font-bold text-white">No Vendor Selected</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Please add a vendor in the Vendor Management Directory first to generate an AI risk assessment.
          </p>
        </div>
      ) : isLoadingAssessment ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <Loader2 className="w-8 h-8 text-cyber-cyan animate-spin mb-3" />
          <p className="text-sm text-slate-400">Loading AI Risk Scorecard for {selectedVendor?.name}...</p>
        </div>
      ) : isAssessmentError || !assessment ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <AlertTriangle className="w-12 h-12 text-amber-400 mb-3" />
          <h3 className="text-lg font-semibold text-white">No Assessment Found for {selectedVendor?.name}</h3>
          <p className="text-xs text-slate-400 max-w-md mt-2">
            This vendor has policy documents stored, but has not yet been evaluated by the AI Risk Engine.
          </p>
        </div>
      ) : (
        <>
          {/* Executive Overall Score Summary */}
          <div className="glass-panel p-6 rounded-xl border border-border flex flex-col md:flex-row justify-between items-center gap-6 bg-gradient-to-r from-slate-900/90 to-surface/80">
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-white uppercase tracking-wider">{selectedVendor?.name}</span>
                <span className={`px-3 py-1 rounded-full border text-xs font-bold ${getTierBadge(assessment.risk_tier)}`}>
                  {assessment.risk_tier} Risk Tier
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {assessment.summary || 'Executive evaluation generated from stored policy content.'}
              </p>
              <div className="text-[11px] text-slate-500 font-mono">
                Assessment Date: {new Date(assessment.assessment_date).toLocaleString()}
              </div>
            </div>

            <div className="text-center p-4 rounded-xl bg-slate-900/90 border border-border min-w-[180px]">
              <span className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">Overall Risk Score</span>
              <div className={`text-4xl font-extrabold mt-1 ${assessment.overall_score >= 50 ? 'text-rose-400' : 'text-emerald-400'}`}>
                {assessment.overall_score.toFixed(1)}
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Weighted 0-100 scale</span>
            </div>
          </div>

          {/* 4 Category Scorecards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="glass-panel p-5 rounded-xl border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Privacy Risk (30%)</span>
                <Lock className="w-4 h-4 text-cyber-cyan" />
              </div>
              <div className="text-2xl font-bold text-white">{privacyCat.score.toFixed(1)} / 100</div>
              <p className="text-[11px] text-slate-400 leading-snug">{privacyCat.justification}</p>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Security Posture (30%)</span>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white">{securityCat.score.toFixed(1)} / 100</div>
              <p className="text-[11px] text-slate-400 leading-snug">{securityCat.justification}</p>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Compliance Risk (20%)</span>
                <FileText className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-white">{complianceCat.score.toFixed(1)} / 100</div>
              <p className="text-[11px] text-slate-400 leading-snug">{complianceCat.justification}</p>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-border space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span>Legal Risk (20%)</span>
                <Scale className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white">{legalCat.score.toFixed(1)} / 100</div>
              <p className="text-[11px] text-slate-400 leading-snug">{legalCat.justification}</p>
            </div>
          </div>

          {/* Evidence-Backed Findings Section */}
          <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyber-cyan" /> Evidence-Backed Risk Findings
              </h3>
              <span className="text-xs text-slate-400">
                {assessment.key_findings?.length || 0} finding(s) extracted
              </span>
            </div>

            {!assessment.key_findings || assessment.key_findings.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No active risk findings identified for this vendor.
              </div>
            ) : (
              <div className="space-y-4">
                {assessment.key_findings.map((finding, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-slate-900/90 border border-border space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-surface text-cyber-cyan border border-cyber-cyan/30">
                          {finding.category}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getTierBadge(finding.severity)}`}>
                          {finding.severity} Severity
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {finding.is_verified ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Verified Evidence Quote
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                            <HelpCircle className="w-3 h-3" /> Unverified Evidence
                          </span>
                        )}
                        <span className="text-[10px] text-slate-500 font-mono">
                          Confidence: {(finding.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-sm font-semibold text-white">{finding.finding}</div>

                    {/* Distinct Evidence Block */}
                    {finding.evidence && (
                      <div className="p-3 rounded-lg bg-surface/80 border-l-2 border-cyber-cyan text-xs italic text-slate-300 flex items-start gap-2">
                        <Quote className="w-4 h-4 text-cyber-cyan flex-shrink-0 mt-0.5" />
                        <div>
                          <span>"{finding.evidence}"</span>
                          {finding.source_url && (
                            <a
                              href={finding.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="block mt-1 font-mono text-[10px] text-cyber-cyan not-italic hover:underline flex items-center gap-1"
                            >
                              Source: {finding.source_url} <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    )}

                    {finding.recommendation && (
                      <div className="text-xs text-slate-300 bg-slate-800/40 p-2.5 rounded-lg border border-border/50">
                        <span className="font-semibold text-cyber-cyan">Recommendation: </span>
                        {finding.recommendation}
                      </div>
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
