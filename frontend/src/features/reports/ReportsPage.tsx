import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  FileText,
  Download,
  Printer,
  Building2,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ExternalLink,
  Loader2,
  Sparkles,
  Calendar,
  Hash,
  Quote,
  RefreshCw,
  Search,
  Check,
} from 'lucide-react';
import { vendorApi, riskApi, reportsApi } from '../../services/api';
import { Vendor, VendorSecurityReport, RiskTier } from '../../types';

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [downloadingFormat, setDownloadingFormat] = useState<'md' | 'pdf' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // 1. Fetch Registered Vendors
  const {
    data: vendors = [],
    isLoading: isLoadingVendors,
    isError: isVendorsError,
    error: vendorsError,
  } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Auto-select first vendor when vendors list loads
  useEffect(() => {
    if (vendors.length > 0 && !selectedVendorId) {
      setSelectedVendorId(vendors[0].id);
    }
  }, [vendors, selectedVendorId]);

  // 2. Fetch Selected Vendor Executive Report
  const {
    data: report,
    isLoading: isLoadingReport,
    isFetching: isFetchingReport,
    isError: isReportError,
    error: reportError,
    refetch: refetchReport,
  } = useQuery<VendorSecurityReport>({
    queryKey: ['vendor-report', selectedVendorId],
    queryFn: () => reportsApi.getVendorReport(selectedVendorId!),
    enabled: !!selectedVendorId,
  });

  // 3. Mutation: Run AI Risk Assessment if unassessed
  const analyzeVendorMutation = useMutation({
    mutationFn: (vendorId: string) => riskApi.analyzeVendor(vendorId),
    onSuccess: (assessment) => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['vendor-report', selectedVendorId] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessment', selectedVendorId] });
      setActionSuccess(`Risk assessment completed! Overall Score: ${assessment.overall_score} (${assessment.risk_tier})`);
      setTimeout(() => setActionSuccess(null), 5000);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Risk assessment failed.';
      setActionError(typeof msg === 'string' ? msg : JSON.stringify(msg));
      setTimeout(() => setActionError(null), 7000);
    },
  });

  // Download Handlers
  const handleDownloadMarkdown = async () => {
    if (!report || !selectedVendorId) return;
    try {
      setDownloadingFormat('md');
      setActionError(null);
      const filename = `${report.vendor.name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_security_report.md`;
      await reportsApi.downloadReportMarkdown(selectedVendorId, filename);
      setActionSuccess('Markdown report downloaded successfully.');
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError('Failed to download Markdown report.');
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDownloadPdf = async () => {
    if (!report || !selectedVendorId) return;
    try {
      setDownloadingFormat('pdf');
      setActionError(null);
      const filename = `${report.vendor.name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}_executive_assessment.pdf`;
      await reportsApi.downloadReportPdf(selectedVendorId, filename);
      setActionSuccess('Executive PDF report downloaded successfully.');
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError('Failed to export Executive PDF report.');
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  // Filtered vendors for master selector
  const filteredVendors = vendors.filter((v) =>
    v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    v.domain.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTierBadge = (tier: string) => {
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

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-rose-400';
    if (score >= 50) return 'text-orange-400';
    if (score >= 30) return 'text-amber-400';
    return 'text-emerald-400';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 70) return 'bg-rose-500';
    if (score >= 50) return 'bg-orange-500';
    if (score >= 30) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Security Assessment Reports"
        description="Evidence-backed vendor risk evaluations, verifiable policy citations, and multi-format publication exports."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              disabled={!report}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 border border-border text-slate-300 hover:text-white font-medium text-xs rounded-lg transition-colors disabled:opacity-40"
              title="Print browser view"
            >
              <Printer className="w-3.5 h-3.5" /> Print
            </button>
            <button
              onClick={handleDownloadMarkdown}
              disabled={!report || downloadingFormat !== null}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-surface border border-cyber-cyan/30 text-cyber-cyan font-semibold text-xs rounded-lg hover:bg-cyber-cyan/10 transition-colors disabled:opacity-40"
            >
              {downloadingFormat === 'md' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5" />
              )}
              Download Markdown
            </button>
            <button
              onClick={handleDownloadPdf}
              disabled={!report || downloadingFormat !== null}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-bold text-xs rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40 shadow-sm"
            >
              {downloadingFormat === 'pdf' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Export Executive PDF
            </button>
          </div>
        }
      />

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}
      {actionError && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* Main Layout: Master Selector Sidebar + Report Detail Canvas */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Vendor Catalog Selector */}
        <div className="lg:col-span-4 glass-panel p-4 rounded-xl border border-border space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Building2 className="w-4 h-4 text-cyber-cyan" />
              Vendors ({vendors.length})
            </h3>
            {isFetchingReport && <Loader2 className="w-3.5 h-3.5 animate-spin text-cyber-cyan" />}
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search vendor or domain..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-900/80 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan transition-colors"
            />
          </div>

          {/* Vendors list */}
          {isLoadingVendors ? (
            <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center gap-2 text-xs">
              <Loader2 className="w-5 h-5 text-cyber-cyan animate-spin" />
              Loading vendors...
            </div>
          ) : filteredVendors.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs bg-surface/50 rounded-lg border border-border">
              No matching vendors found.
            </div>
          ) : (
            <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
              {filteredVendors.map((v) => {
                const isSelected = v.id === selectedVendorId;
                return (
                  <button
                    key={v.id}
                    onClick={() => setSelectedVendorId(v.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-cyber-cyan/10 border-cyber-cyan shadow-sm text-white'
                        : 'bg-slate-900/60 border-border hover:bg-slate-900 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-semibold text-xs text-white truncate max-w-[160px]">
                        {v.name}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${getTierBadge(
                          v.risk_tier
                        )}`}
                      >
                        {v.risk_tier}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                      <span className="truncate max-w-[150px]">{v.domain}</span>
                      <span className={`font-bold ${getScoreColor(v.current_risk_score)}`}>
                        {v.current_risk_score.toFixed(1)} / 100
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Interactive Executive Security Report */}
        <div className="lg:col-span-8 space-y-6">
          {isLoadingReport ? (
            <div className="glass-panel p-16 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[450px]">
              <Loader2 className="w-8 h-8 text-cyber-cyan animate-spin mb-3" />
              <p className="text-sm text-slate-300 font-medium">Assembling Executive Security Report...</p>
              <p className="text-xs text-slate-500 mt-1">Aggregating evidence, findings, and category scores.</p>
            </div>
          ) : isReportError || !report ? (
            <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[400px]">
              <AlertCircle className="w-10 h-10 text-rose-400 mb-3" />
              <h3 className="text-base font-bold text-white">Unable to Load Assessment Report</h3>
              <p className="text-xs text-slate-400 max-w-md mt-1 mb-4">
                {(reportError as any)?.response?.data?.detail || 'An unexpected error occurred while compiling the report.'}
              </p>
              <button
                onClick={() => refetchReport()}
                className="px-4 py-2 bg-surface border border-border text-slate-300 hover:text-white rounded-lg text-xs font-semibold flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry
              </button>
            </div>
          ) : (
            <>
              {/* Report Header Card */}
              <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-mono tracking-wider uppercase font-semibold bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/30">
                        CONFIDENTIAL // SECURITY AUDIT
                      </span>
                      <span className="text-slate-500 text-xs">•</span>
                      <span className="text-xs text-slate-400">
                        Generated {new Date(report.generated_at).toLocaleString()}
                      </span>
                    </div>
                    <h2 className="text-2xl font-bold text-white mt-1 flex items-center gap-2">
                      <Building2 className="w-6 h-6 text-cyber-cyan" />
                      {report.vendor.name}
                    </h2>
                    <div className="flex items-center gap-4 text-xs text-slate-400 mt-1 font-mono">
                      <span>Domain: <span className="text-slate-200">{report.vendor.domain}</span></span>
                      <a
                        href={report.vendor.website_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-cyber-cyan hover:underline flex items-center gap-1"
                      >
                        Visit Site <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">
                        Overall Risk Tier
                      </div>
                      <span
                        className={`inline-block mt-0.5 px-3 py-1 rounded-full border text-xs font-extrabold ${getTierBadge(
                          report.executive_summary.overall_risk_tier
                        )}`}
                      >
                        {report.executive_summary.overall_risk_tier.toUpperCase()} RISK
                      </span>
                    </div>
                    <div className="h-10 w-px bg-border hidden sm:block" />
                    <div className="text-right">
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">
                        Risk Score
                      </div>
                      <div
                        className={`text-2xl font-black ${getScoreColor(
                          report.executive_summary.overall_score
                        )}`}
                      >
                        {report.executive_summary.overall_score.toFixed(1)}
                        <span className="text-xs font-normal text-slate-500"> / 100</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Status Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-medium">Policy Posture</span>
                    <span className="font-semibold text-slate-200">{report.executive_summary.policy_posture}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-medium">Monitoring Cadence</span>
                    <span className="font-semibold text-slate-200">{report.vendor.monitoring_frequency}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-medium">Policy Documents</span>
                    <span className="font-semibold text-slate-200">{report.policy_snapshots.length} Tracked</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-border">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-medium">Policy Drift</span>
                    <span className={`font-semibold ${report.executive_summary.policy_changes_detected ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {report.executive_summary.policy_changes_detected ? 'Changes Detected' : 'Unchanged'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Unassessed Warning Banner */}
              {!report.has_assessment_data && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                    <div>
                      <span className="font-bold text-amber-400 block">Preliminary Vendor Record</span>
                      <span className="text-slate-300">
                        This vendor has not undergone an AI risk assessment yet. Scores and findings are provisional.
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => analyzeVendorMutation.mutate(report.vendor.vendor_id)}
                    disabled={analyzeVendorMutation.isPending}
                    className="px-3.5 py-2 bg-amber-500 text-black font-bold rounded-lg hover:bg-amber-400 transition-colors flex items-center gap-1.5 shrink-0 self-start sm:self-auto disabled:opacity-50"
                  >
                    {analyzeVendorMutation.isPending ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Analyzing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" /> Run AI Assessment
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Executive Summary */}
              <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-border pb-3">
                  <FileText className="w-4 h-4 text-cyber-cyan" /> Executive Summary
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {report.executive_summary.summary_text}
                </p>

                {report.executive_summary.key_highlights && report.executive_summary.key_highlights.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Key Highlights
                    </span>
                    <ul className="space-y-1.5">
                      {report.executive_summary.key_highlights.map((highlight, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                          <Check className="w-3.5 h-3.5 text-cyber-cyan shrink-0 mt-0.5" />
                          <span>{highlight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Category Risk Overview (4 Pillars) */}
              <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-border pb-3">
                  <ShieldCheck className="w-4 h-4 text-cyber-cyan" /> Category Risk Breakdown
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {report.risk_overview.map((cat) => (
                    <div key={cat.category} className="p-4 rounded-xl bg-slate-900/70 border border-border space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-white">{cat.category}</span>
                        <span className={`font-mono font-bold text-xs ${getScoreColor(cat.score)}`}>
                          {cat.score.toFixed(1)} / 100
                        </span>
                      </div>
                      {/* Score Bar */}
                      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${getScoreBarColor(cat.score)} transition-all duration-500`}
                          style={{ width: `${Math.min(100, Math.max(0, cat.score))}%` }}
                        />
                      </div>
                      {cat.justification && (
                        <p className="text-[11px] text-slate-400 leading-relaxed pt-1">
                          {cat.justification}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Risk Findings */}
              <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-cyber-cyan" /> Key Findings ({report.findings.length})
                  </h3>
                  <span className="text-[11px] text-slate-500 font-mono">
                    {report.findings.filter((f) => f.is_verified).length} Verified by Policy Citations
                  </span>
                </div>

                {report.findings.length === 0 ? (
                  <div className="p-4 text-center text-slate-400 text-xs bg-surface/50 rounded-lg">
                    No critical risk findings recorded for this vendor.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {report.findings.map((finding, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-slate-900/80 border border-border space-y-2 text-xs"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-slate-200">
                              {finding.finding}
                            </span>
                            {finding.is_verified && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" /> Verified Evidence
                              </span>
                            )}
                          </div>
                          <span
                            className={`px-2.5 py-0.5 rounded-full border text-[10px] font-bold shrink-0 ${getTierBadge(
                              finding.severity
                            )}`}
                          >
                            {finding.severity}
                          </span>
                        </div>

                        {finding.evidence && (
                          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-border/60 text-[11px] text-slate-300 font-mono italic">
                            "{finding.evidence}"
                          </div>
                        )}

                        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                          <span className="font-medium text-slate-500 uppercase tracking-wider">
                            Category: <span className="text-slate-300">{finding.category}</span>
                          </span>
                          {finding.source_url && (
                            <a
                              href={finding.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-cyber-cyan hover:underline flex items-center gap-1 font-mono"
                            >
                              Source <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>

                        {finding.recommendation && (
                          <div className="text-[11px] text-slate-300 bg-cyber-blue/10 border border-cyber-blue/20 p-2 rounded-lg">
                            <span className="font-semibold text-cyber-blue">Recommendation: </span>
                            {finding.recommendation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Verified Evidence Quotes */}
              {report.evidence && report.evidence.length > 0 && (
                <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-border pb-3">
                    <Quote className="w-4 h-4 text-cyber-cyan" /> Verified Policy Citations ({report.evidence.length})
                  </h3>

                  <div className="space-y-3">
                    {report.evidence.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-slate-900/60 border border-border space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-cyber-cyan font-mono">
                            [{item.category}] {item.document_type} - {item.title}
                          </span>
                          {item.source_url && (
                            <a
                              href={item.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-slate-400 hover:text-white flex items-center gap-1 font-mono"
                            >
                              Document Link <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                        <blockquote className="border-l-2 border-cyber-cyan pl-3 py-1 text-slate-300 text-[11px] italic bg-slate-950/40 rounded-r">
                          "{item.quote}"
                        </blockquote>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actionable Recommendations */}
              {report.recommendations && report.recommendations.length > 0 && (
                <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-border pb-3">
                    <Sparkles className="w-4 h-4 text-cyber-cyan" /> Actionable Mitigations & Recommendations
                  </h3>

                  <div className="space-y-2">
                    {report.recommendations.map((rec, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-slate-900/70 border border-border flex items-start gap-2.5 text-xs text-slate-300"
                      >
                        <span className="w-5 h-5 rounded-full bg-cyber-cyan/20 text-cyber-cyan font-mono text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                          {idx + 1}
                        </span>
                        <span className="leading-relaxed">{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Policy Snapshot Versioning */}
              <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Hash className="w-4 h-4 text-cyber-cyan" /> Discovered Policy Documents & Hashes ({report.policy_snapshots.length})
                  </h3>
                </div>

                {report.policy_snapshots.length === 0 ? (
                  <div className="p-4 text-center text-slate-400 text-xs bg-surface/50 rounded-lg">
                    No policy documents indexed for this vendor.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-border text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                          <th className="py-2.5 px-3">Type</th>
                          <th className="py-2.5 px-3">Document Title</th>
                          <th className="py-2.5 px-3 font-mono">SHA-256 Hash</th>
                          <th className="py-2.5 px-3">Version</th>
                          <th className="py-2.5 px-3">Last Crawled</th>
                          <th className="py-2.5 px-3">Status / Drift</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {report.policy_snapshots.map((snap) => (
                          <tr key={snap.document_id} className="hover:bg-slate-900/40">
                            <td className="py-2.5 px-3 font-semibold text-white">{snap.document_type}</td>
                            <td className="py-2.5 px-3 text-slate-300 max-w-[200px] truncate">
                              <a
                                href={snap.url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:text-cyber-cyan flex items-center gap-1 font-mono"
                              >
                                {snap.title} <ExternalLink className="w-3 h-3 shrink-0" />
                              </a>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                              {snap.current_version_hash ? (
                                <span title={snap.current_version_hash}>
                                  {snap.current_version_hash.slice(0, 12)}...
                                </span>
                              ) : (
                                <span className="text-slate-600">Pending</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 font-mono text-slate-300">v{snap.version_number}</td>
                            <td className="py-2.5 px-3 text-slate-400">
                              {snap.last_crawled_at
                                ? new Date(snap.last_crawled_at).toLocaleDateString()
                                : 'Never'}
                            </td>
                            <td className="py-2.5 px-3">
                              {snap.change_summary ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                  Updated
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                  Baseline
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
