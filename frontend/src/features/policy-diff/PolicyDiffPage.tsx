import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  GitCompare,
  Building2,
  FileText,
  Clock,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Zap,
  ArrowRight,
  ArrowLeftRight,
  Columns,
  AlignLeft,
  Loader2,
  Info,
  Quote,
  ShieldAlert,
  ChevronDown,
} from 'lucide-react';
import { vendorApi, policyDiffApi } from '../../services/api';
import {
  Vendor,
  Document,
  PolicyVersionSummary,
  PolicyDiffResponse,
  MaterialityTier,
  RiskPostureImpact,
  RiskPillar,
} from '../../types';

export const PolicyDiffPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const paramVendorId = searchParams.get('vendorId') || '';
  const paramDocId = searchParams.get('documentId') || '';
  const paramV1 = searchParams.get('v1') || '';
  const paramV2 = searchParams.get('v2') || '';

  const [selectedVendorId, setSelectedVendorId] = useState<string>(paramVendorId);
  const [selectedDocId, setSelectedDocId] = useState<string>(paramDocId);
  const [versionAId, setVersionAId] = useState<string>(paramV1);
  const [versionBId, setVersionBId] = useState<string>(paramV2);
  const [viewMode, setViewMode] = useState<'side-by-side' | 'unified'>('side-by-side');

  // 1. Fetch Vendors
  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Auto-select initial vendor
  useEffect(() => {
    if (!selectedVendorId && vendors.length > 0) {
      setSelectedVendorId(vendors[0].id);
    }
  }, [vendors, selectedVendorId]);

  // 2. Fetch Documents for Selected Vendor
  const { data: documents = [], isLoading: isLoadingDocs } = useQuery<Document[]>({
    queryKey: ['vendor-documents', selectedVendorId],
    queryFn: () => vendorApi.getVendorDocuments(selectedVendorId),
    enabled: !!selectedVendorId,
  });

  // Auto-select initial document
  useEffect(() => {
    if (documents.length > 0) {
      const exists = documents.some((d) => d.id === selectedDocId);
      if (!exists) {
        setSelectedDocId(documents[0].id);
      }
    } else {
      setSelectedDocId('');
    }
  }, [documents, selectedDocId]);

  // 3. Fetch Versions for Selected Document
  const { data: versions = [], isLoading: isLoadingVersions } = useQuery<PolicyVersionSummary[]>({
    queryKey: ['document-versions', selectedVendorId, selectedDocId],
    queryFn: () => policyDiffApi.getDocumentVersions(selectedVendorId, selectedDocId),
    enabled: !!selectedVendorId && !!selectedDocId,
  });

  // Auto-select comparison versions when versions load
  useEffect(() => {
    if (versions.length >= 2) {
      // Default: Version A is older (v1), Version B is newer (v2)
      const sorted = [...versions].sort((a, b) => a.version_number - b.version_number);
      const vOld = sorted[sorted.length - 2].id;
      const vNew = sorted[sorted.length - 1].id;

      if (!versionAId || !versions.some((v) => v.id === versionAId)) {
        setVersionAId(vOld);
      }
      if (!versionBId || !versions.some((v) => v.id === versionBId)) {
        setVersionBId(vNew);
      }
    } else if (versions.length === 1) {
      setVersionAId(versions[0].id);
      setVersionBId(versions[0].id);
    }
  }, [versions, versionAId, versionBId]);

  // 4. Fetch Diff & Semantic Impact
  const canCompare = !!selectedVendorId && !!selectedDocId && !!versionAId && !!versionBId;

  const {
    data: diffData,
    isLoading: isLoadingDiff,
    isFetching: isFetchingDiff,
    error: diffError,
    refetch: refetchDiff,
  } = useQuery<PolicyDiffResponse>({
    queryKey: ['policy-diff', selectedVendorId, selectedDocId, versionAId, versionBId],
    queryFn: () => policyDiffApi.getPolicyDiff(selectedVendorId, selectedDocId, versionAId, versionBId),
    enabled: canCompare,
    staleTime: 1000 * 60 * 10, // 10 mins cache in react-query
  });

  // Keep query params in sync
  const updateUrlParams = (vId: string, dId: string, v1: string, v2: string) => {
    const nextParams = new URLSearchParams();
    if (vId) nextParams.set('vendorId', vId);
    if (dId) nextParams.set('documentId', dId);
    if (v1) nextParams.set('v1', v1);
    if (v2) nextParams.set('v2', v2);
    setSearchParams(nextParams, { replace: true });
  };

  const handleVendorChange = (vId: string) => {
    setSelectedVendorId(vId);
    setSelectedDocId('');
    setVersionAId('');
    setVersionBId('');
    updateUrlParams(vId, '', '', '');
  };

  const handleDocChange = (dId: string) => {
    setSelectedDocId(dId);
    setVersionAId('');
    setVersionBId('');
    updateUrlParams(selectedVendorId, dId, '', '');
  };

  const handleSwapVersions = () => {
    const temp = versionAId;
    setVersionAId(versionBId);
    setVersionBId(temp);
    updateUrlParams(selectedVendorId, selectedDocId, versionBId, temp);
  };

  // Badges & styling helpers
  const getMaterialityBadge = (mat: MaterialityTier) => {
    switch (mat) {
      case 'Critical':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'High':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'Medium':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'Low':
      default:
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
  };

  const getPostureBadge = (posture: RiskPostureImpact) => {
    switch (posture) {
      case 'Adverse':
        return {
          bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
          label: 'Adverse Risk Impact',
          icon: <AlertTriangle className="w-3.5 h-3.5 mr-1 text-rose-400" />,
        };
      case 'Favorable':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          label: 'Favorable Posture Improvement',
          icon: <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />,
        };
      case 'Neutral':
      default:
        return {
          bg: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
          label: 'Neutral / Nominal Change',
          icon: <Info className="w-3.5 h-3.5 mr-1 text-slate-400" />,
        };
    }
  };

  const getPillarBadge = (pillar: RiskPillar) => {
    switch (pillar) {
      case 'Privacy':
        return 'bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/30';
      case 'Security':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'Compliance':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'Legal':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'Multiple':
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    }
  };

  const selectedVendor = vendors.find((v) => v.id === selectedVendorId);
  const selectedDoc = documents.find((d) => d.id === selectedDocId);
  const versionA = versions.find((v) => v.id === versionAId);
  const versionB = versions.find((v) => v.id === versionBId);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Policy Diff & Semantic Change Analyzer"
        description="Deterministic line-by-line diff and LLM-powered contractual, security, and privacy risk impact attribution."
      />

      {/* Control Panel: Vendor, Document, & Version Selection */}
      <div className="glass-panel p-5 rounded-xl border border-border space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Vendor Selector */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
              <Building2 className="w-3.5 h-3.5 text-cyber-cyan" /> 1. Vendor
            </label>
            <select
              value={selectedVendorId}
              onChange={(e) => handleVendorChange(e.target.value)}
              disabled={isLoadingVendors || vendors.length === 0}
              className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-cyber-cyan"
            >
              {vendors.length === 0 ? (
                <option value="">No registered vendors</option>
              ) : (
                vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.domain})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Document Selector */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-emerald-400" /> 2. Policy Document
            </label>
            <select
              value={selectedDocId}
              onChange={(e) => handleDocChange(e.target.value)}
              disabled={isLoadingDocs || documents.length === 0}
              className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-cyber-cyan"
            >
              {documents.length === 0 ? (
                <option value="">No crawled documents</option>
              ) : (
                documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.document_type} ({d.title})
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Version A (Baseline) */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-amber-400" /> 3. Baseline (Older)
            </label>
            <select
              value={versionAId}
              onChange={(e) => {
                setVersionAId(e.target.value);
                updateUrlParams(selectedVendorId, selectedDocId, e.target.value, versionBId);
              }}
              disabled={isLoadingVersions || versions.length === 0}
              className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-cyber-cyan"
            >
              {versions.length === 0 ? (
                <option value="">No version snapshots</option>
              ) : (
                versions.map((ver) => (
                  <option key={ver.id} value={ver.id}>
                    v{ver.version_number} — {new Date(ver.crawled_at).toLocaleDateString()} ({ver.line_count} lines)
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Version B (Comparison) */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-purple-400" /> 4. Comparison (Newer)
              </span>
              <button
                type="button"
                onClick={handleSwapVersions}
                title="Swap baseline and comparison"
                className="text-slate-400 hover:text-cyber-cyan transition-colors"
              >
                <ArrowLeftRight className="w-3 h-3" />
              </button>
            </label>
            <select
              value={versionBId}
              onChange={(e) => {
                setVersionBId(e.target.value);
                updateUrlParams(selectedVendorId, selectedDocId, versionAId, e.target.value);
              }}
              disabled={isLoadingVersions || versions.length === 0}
              className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-xs text-white focus:outline-none focus:border-cyber-cyan"
            >
              {versions.length === 0 ? (
                <option value="">No version snapshots</option>
              ) : (
                versions.map((ver) => (
                  <option key={ver.id} value={ver.id}>
                    v{ver.version_number} — {new Date(ver.crawled_at).toLocaleDateString()} ({ver.line_count} lines)
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        {/* View Mode Switcher and Compare Trigger */}
        <div className="flex flex-wrap justify-between items-center gap-3 pt-3 border-t border-border text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Diff Layout:</span>
            <div className="flex rounded-lg bg-slate-900 p-0.5 border border-border">
              <button
                type="button"
                onClick={() => setViewMode('side-by-side')}
                className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 text-xs font-semibold transition-all ${
                  viewMode === 'side-by-side'
                    ? 'bg-cyber-cyan/20 text-cyber-cyan shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Columns className="w-3.5 h-3.5" /> Side-by-Side
              </button>
              <button
                type="button"
                onClick={() => setViewMode('unified')}
                className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 text-xs font-semibold transition-all ${
                  viewMode === 'unified'
                    ? 'bg-cyber-cyan/20 text-cyber-cyan shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <AlignLeft className="w-3.5 h-3.5" /> Unified Diff
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {diffData?.is_cached && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <Zap className="w-3 h-3 text-emerald-400" /> Instant Cached Analysis
              </span>
            )}
            <button
              type="button"
              onClick={() => refetchDiff()}
              disabled={isFetchingDiff || !canCompare}
              className="px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-slate-950 font-bold rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
            >
              {isFetchingDiff ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Evaluating Diff...
                </>
              ) : (
                <>
                  <GitCompare className="w-4 h-4" /> Compare Versions
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Main Diff Content */}
      {isLoadingDiff ? (
        <div className="glass-panel p-16 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <Loader2 className="w-10 h-10 text-cyber-cyan animate-spin mb-4" />
          <h4 className="text-base font-bold text-white">Analyzing Policy Differences</h4>
          <p className="text-xs text-slate-400 max-w-md mt-1">
            Computing deterministic word-level delta and synthesizing AI semantic change impact...
          </p>
        </div>
      ) : diffError ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <AlertTriangle className="w-10 h-10 text-amber-400 mb-3" />
          <h4 className="text-base font-bold text-white">Unable to Compare Versions</h4>
          <p className="text-xs text-slate-400 max-w-md mt-1">
            {(diffError as any)?.response?.data?.detail || (diffError as Error).message}
          </p>
        </div>
      ) : !diffData ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <GitCompare className="w-12 h-12 text-slate-600 mb-3" />
          <h4 className="text-base font-bold text-white">Select Versions to Compare</h4>
          <p className="text-xs text-slate-400 max-w-md mt-1">
            Select a vendor, document, and two policy version snapshots above to view deterministic line changes and AI risk impact.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Executive AI Semantic Impact Card */}
          <div className="glass-panel p-6 rounded-xl border border-border bg-gradient-to-br from-slate-900/95 via-surface/90 to-slate-900/95 space-y-5">
            {/* Header: Materiality, Pillar, & Posture */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-cyber-cyan" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    AI Semantic Change Impact Analysis
                    <span className="text-xs font-normal text-slate-400">
                      ({diffData.document_type}: v{diffData.old_version.version_number} → v{diffData.new_version.version_number})
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Category: {diffData.semantic_impact.clause_category}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${getMaterialityBadge(diffData.semantic_impact.materiality)}`}>
                  {diffData.semantic_impact.materiality} Materiality
                </span>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${getPillarBadge(diffData.semantic_impact.affected_risk_pillar)}`}>
                  {diffData.semantic_impact.affected_risk_pillar} Risk
                </span>
                {(() => {
                  const posture = getPostureBadge(diffData.semantic_impact.risk_posture);
                  return (
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold border flex items-center ${posture.bg}`}>
                      {posture.icon}
                      {posture.label}
                    </span>
                  );
                })()}
              </div>
            </div>

            {/* Executive Change Summary */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider text-cyber-cyan">
                Executive Synthesis
              </h4>
              <p className="text-xs text-slate-200 leading-relaxed bg-slate-900/70 p-3.5 rounded-lg border border-border/70">
                {diffData.semantic_impact.executive_change_summary}
              </p>
            </div>

            {/* Modification Intent & Risk Delta Explanation */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-900/70 p-3.5 rounded-lg border border-border/70 space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Contractual Modification Intent
                </span>
                <p className="text-slate-300">
                  {diffData.semantic_impact.modification_intent || 'General revisions and contractual policy updates.'}
                </p>
              </div>

              <div className="bg-slate-900/70 p-3.5 rounded-lg border border-border/70 space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Risk Delta Attribution
                </span>
                <p className="text-slate-300">
                  {diffData.semantic_impact.risk_delta_explanation || 'Risk posture evaluation based on policy changes.'}
                </p>
              </div>
            </div>

            {/* Clause Breakdown (if present) */}
            {diffData.semantic_impact.clause_breakdown && diffData.semantic_impact.clause_breakdown.length > 0 && (
              <div className="space-y-3 pt-2">
                <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Specific Clause Modifications ({diffData.semantic_impact.clause_breakdown.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {diffData.semantic_impact.clause_breakdown.map((item, idx) => (
                    <div key={idx} className="p-3 bg-slate-900/90 border border-border rounded-lg space-y-1.5 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-white">{item.clause_title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-border">
                          {item.change_type} • {item.risk_pillar}
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px]">{item.intent}</p>
                      {item.quote && (
                        <p className="text-slate-400 italic text-[10px] bg-surface p-2 rounded border-l-2 border-cyber-cyan">
                          "{item.quote}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Deterministic Diff Metrics Banner */}
          <div className="glass-panel p-4 rounded-xl border border-border flex flex-wrap justify-between items-center gap-4 text-xs font-mono">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-slate-400 font-sans font-semibold">Diff Summary:</span>
              <span className="text-emerald-400 font-bold">
                +{diffData.deterministic_diff.stats.added_lines} line(s) added
              </span>
              <span className="text-rose-400 font-bold">
                -{diffData.deterministic_diff.stats.deleted_lines} line(s) removed
              </span>
              <span className="text-cyber-cyan font-bold">
                {diffData.deterministic_diff.stats.changed_lines} modified line(s)
              </span>
            </div>

            <div className="text-slate-400 text-[11px]">
              Baseline: v{diffData.old_version.version_number} ({diffData.old_version.line_count} lines) → Comparison: v{diffData.new_version.version_number} ({diffData.new_version.line_count} lines)
            </div>
          </div>

          {/* Truncation warning if present */}
          {diffData.deterministic_diff.stats.is_truncated && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center gap-2">
              <Info className="w-4 h-4 flex-shrink-0" />
              <span>{diffData.deterministic_diff.stats.truncation_note}</span>
            </div>
          )}

          {/* Identical Versions Banner */}
          {diffData.deterministic_diff.stats.is_identical && (
            <div className="glass-panel p-10 rounded-xl border border-border text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <h4 className="text-base font-bold text-white">Identical Policy Versions</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No text modifications detected between version v{diffData.old_version.version_number} and version v{diffData.new_version.version_number}. The policy content is identical.
              </p>
            </div>
          )}

          {/* Visual Diff Viewers */}
          {!diffData.deterministic_diff.stats.is_identical && (
            <div className="glass-panel rounded-xl border border-border overflow-hidden">
              <div className="p-3 bg-slate-900 border-b border-border flex justify-between items-center text-xs">
                <span className="font-bold text-white flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-cyber-cyan" />
                  {viewMode === 'side-by-side' ? 'Side-by-Side Visual Diff' : 'Unified Diff View'}
                </span>
                <span className="text-[11px] text-slate-400">
                  {diffData.document_title}
                </span>
              </div>

              {/* Side-by-Side View */}
              {viewMode === 'side-by-side' ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-[11px] font-mono leading-relaxed">
                    <thead>
                      <tr className="bg-slate-900/90 text-slate-400 border-b border-border">
                        <th className="w-12 px-2 py-2 text-center">#</th>
                        <th className="w-1/2 px-3 py-2 border-r border-border text-slate-300">
                          v{diffData.old_version.version_number} ({new Date(diffData.old_version.crawled_at).toLocaleDateString()})
                        </th>
                        <th className="w-12 px-2 py-2 text-center">#</th>
                        <th className="w-1/2 px-3 py-2 text-slate-300">
                          v{diffData.new_version.version_number} ({new Date(diffData.new_version.crawled_at).toLocaleDateString()})
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {diffData.deterministic_diff.side_by_side_rows.map((row, idx) => {
                        let leftBg = '';
                        let rightBg = '';

                        if (row.row_type === 'deleted') {
                          leftBg = 'bg-rose-950/40 text-rose-200';
                          rightBg = 'bg-slate-950/40';
                        } else if (row.row_type === 'added') {
                          leftBg = 'bg-slate-950/40';
                          rightBg = 'bg-emerald-950/40 text-emerald-200';
                        } else if (row.row_type === 'modified') {
                          leftBg = 'bg-rose-950/30 text-rose-200';
                          rightBg = 'bg-emerald-950/30 text-emerald-200';
                        } else {
                          leftBg = 'text-slate-300';
                          rightBg = 'text-slate-300';
                        }

                        return (
                          <tr key={idx} className="border-b border-border/30 hover:bg-slate-800/40">
                            {/* Left Line No */}
                            <td className="px-2 py-1 text-center select-none text-slate-500 bg-slate-900/60 border-r border-border/30">
                              {row.left_line_no || ''}
                            </td>
                            {/* Left Content */}
                            <td className={`px-3 py-1 border-r border-border/40 whitespace-pre-wrap break-words ${leftBg}`}>
                              {row.left_words ? (
                                row.left_words.map((w, wIdx) => (
                                  <span
                                    key={wIdx}
                                    className={
                                      w.type === 'deleted'
                                        ? 'bg-rose-600/40 text-rose-100 rounded px-0.5'
                                        : ''
                                    }
                                  >
                                    {w.text}
                                  </span>
                                ))
                              ) : (
                                row.left_content || ''
                              )}
                            </td>

                            {/* Right Line No */}
                            <td className="px-2 py-1 text-center select-none text-slate-500 bg-slate-900/60 border-r border-border/30">
                              {row.right_line_no || ''}
                            </td>
                            {/* Right Content */}
                            <td className={`px-3 py-1 whitespace-pre-wrap break-words ${rightBg}`}>
                              {row.right_words ? (
                                row.right_words.map((w, wIdx) => (
                                  <span
                                    key={wIdx}
                                    className={
                                      w.type === 'added'
                                        ? 'bg-emerald-600/40 text-emerald-100 rounded px-0.5'
                                        : ''
                                    }
                                  >
                                    {w.text}
                                  </span>
                                ))
                              ) : (
                                row.right_content || ''
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                /* Unified View */
                <div className="divide-y divide-border/40 font-mono text-[11px] leading-relaxed">
                  {diffData.deterministic_diff.unified_hunks.map((hunk, hIdx) => (
                    <div key={hIdx} className="space-y-0.5">
                      {/* Hunk Header */}
                      <div className="px-4 py-1.5 bg-slate-800 text-cyber-cyan font-bold select-none border-b border-border/40">
                        {hunk.header}
                      </div>

                      {/* Hunk Lines */}
                      {hunk.lines.map((line, lIdx) => {
                        let lineBg = '';
                        let linePrefix = ' ';
                        let prefixColor = 'text-slate-500';

                        if (line.type === 'added') {
                          lineBg = 'bg-emerald-950/40 text-emerald-200';
                          linePrefix = '+';
                          prefixColor = 'text-emerald-400';
                        } else if (line.type === 'deleted') {
                          lineBg = 'bg-rose-950/40 text-rose-200';
                          linePrefix = '-';
                          prefixColor = 'text-rose-400';
                        } else {
                          lineBg = 'text-slate-300';
                        }

                        return (
                          <div
                            key={lIdx}
                            className={`flex items-start px-3 py-0.5 hover:bg-slate-800/40 ${lineBg}`}
                          >
                            <span className="w-10 text-right pr-2 text-slate-500 select-none">
                              {line.old_line_no || ''}
                            </span>
                            <span className="w-10 text-right pr-3 text-slate-500 select-none">
                              {line.new_line_no || ''}
                            </span>
                            <span className={`w-4 font-bold select-none ${prefixColor}`}>
                              {linePrefix}
                            </span>
                            <span className="flex-1 whitespace-pre-wrap break-words">
                              {line.content}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default PolicyDiffPage;
