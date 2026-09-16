import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import { ShieldCheck, Award, FileCheck, Building2, CheckCircle2, AlertTriangle, ExternalLink, Loader2, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { vendorApi, complianceApi } from '../../services/api';
import { Vendor, ComplianceAssessmentResult, ComplianceFrameworkSummary } from '../../types';

export const CompliancePage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [selectedFramework, setSelectedFramework] = useState<string>('All Frameworks');
  const [selectedStatus, setSelectedStatus] = useState<string>('All Statuses');
  const [expandedControl, setExpandedControl] = useState<string | null>(null);

  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  const activeVendorId = selectedVendorId || (vendors.length > 0 ? vendors[0].id : '');

  const { data: complianceData, isLoading: isLoadingCompliance, isFetching: isFetchingCompliance } = useQuery({
    queryKey: ['compliance', activeVendorId, selectedFramework, selectedStatus],
    queryFn: () => complianceApi.getVendorCompliance(activeVendorId, selectedFramework, selectedStatus),
    enabled: !!activeVendorId,
    retry: false
  });

  const frameworks = ['All Frameworks', 'SOC 2 Type II', 'ISO 27001', 'GDPR', 'HIPAA', 'NIST SP 800-53'];
  const statuses = ['All Statuses', 'PASS', 'PARTIAL', 'GAP', 'NOT_ASSESSED'];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASS': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'PARTIAL': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'GAP': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'NOT_ASSESSED': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS': return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'PARTIAL': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'GAP': return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case 'NOT_ASSESSED': return <Info className="w-4 h-4 text-slate-400" />;
      default: return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const renderSummaryCard = (title: string, value: string | number, subtitle: string, icon: React.ReactNode, textColor = 'text-white') => (
    <div className="glass-panel p-5 rounded-xl border border-border">
      <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
        <span>{title}</span>
        {icon}
      </div>
      <div className={`text-3xl font-extrabold mt-2 ${textColor}`}>{value}</div>
      <p className="text-[11px] text-slate-500 mt-1">{subtitle}</p>
    </div>
  );

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Regulatory & Compliance Framework Crosswalk"
        description="Evidence-grounded policy assessment against standard frameworks (SOC2, ISO27001, GDPR, HIPAA, NIST)."
      />

      {/* Selectors */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-emerald-400" />
          <span className="font-semibold text-white">Vendor:</span>
        </div>
        <select
          value={activeVendorId}
          onChange={(e) => setSelectedVendorId(e.target.value)}
          disabled={vendors.length === 0}
          className="w-full sm:w-64 px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
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

        <div className="h-6 w-px bg-border hidden sm:block mx-2" />

        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">Framework:</span>
        </div>
        <select
          value={selectedFramework}
          onChange={(e) => setSelectedFramework(e.target.value)}
          className="w-full sm:w-48 px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
        >
          {frameworks.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">Status:</span>
        </div>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="w-full sm:w-40 px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
        >
          {statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {vendors.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <ShieldCheck className="w-12 h-12 text-emerald-400 mb-4" />
          <h3 className="text-xl font-bold text-white">Compliance Framework Ready</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Register vendors in the catalog to discover compliance documents and evaluate compliance against regulatory frameworks.
          </p>
        </div>
      ) : isLoadingCompliance ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-emerald-400 animate-spin mb-3" />
          <p className="text-sm text-slate-400">Performing evidence-based policy assessment...</p>
          <p className="text-[10px] text-slate-500 mt-2">This may take a minute as we retrieve and verify control evidence.</p>
        </div>
      ) : complianceData ? (
        <>
          {/* Summary Cards */}
          {complianceData.summaries.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {renderSummaryCard(
                'PASS',
                complianceData.summaries.reduce((acc, s) => acc + s.pass_count, 0),
                'Satisfied controls',
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
                'text-emerald-400'
              )}
              {renderSummaryCard(
                'PARTIAL',
                complianceData.summaries.reduce((acc, s) => acc + s.partial_count, 0),
                'Partially addressed',
                <AlertTriangle className="w-4 h-4 text-amber-400" />,
                'text-amber-400'
              )}
              {renderSummaryCard(
                'GAP',
                complianceData.summaries.reduce((acc, s) => acc + s.gap_count, 0),
                'Explicitly failed',
                <AlertTriangle className="w-4 h-4 text-rose-400" />,
                'text-rose-400'
              )}
              {renderSummaryCard(
                'NOT ASSESSED',
                complianceData.summaries.reduce((acc, s) => acc + s.not_assessed_count, 0),
                'No evidence found',
                <Info className="w-4 h-4 text-slate-400" />,
                'text-slate-400'
              )}
              
              {/* Overall Coverage (average of all framework coverages) */}
              {renderSummaryCard(
                'Avg Coverage',
                `${(complianceData.summaries.reduce((acc, s) => acc + s.coverage_percentage, 0) / complianceData.summaries.length || 0).toFixed(1)}%`,
                'Based on assessed frameworks',
                <Award className="w-4 h-4 text-cyber-cyan" />,
                'text-cyber-cyan'
              )}
            </div>
          )}

          {/* Matrix */}
          <div className="glass-panel rounded-xl border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/80 border-b border-border text-xs uppercase text-slate-400">
                    <th className="px-4 py-3 font-medium w-32">Framework</th>
                    <th className="px-4 py-3 font-medium w-24">Control ID</th>
                    <th className="px-4 py-3 font-medium">Control</th>
                    <th className="px-4 py-3 font-medium w-32 text-center">Status</th>
                    <th className="px-4 py-3 font-medium w-24 text-right">Confidence</th>
                    <th className="px-4 py-3 font-medium w-16"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {complianceData.assessments.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-400">
                        No controls found matching the selected criteria.
                      </td>
                    </tr>
                  ) : (
                    complianceData.assessments.map((assessment, idx) => {
                      const isExpanded = expandedControl === `${assessment.framework}-${assessment.control_id}`;
                      
                      return (
                        <React.Fragment key={`${assessment.framework}-${assessment.control_id}-${idx}`}>
                          <tr 
                            className="bg-surface hover:bg-slate-800/50 transition-colors cursor-pointer text-sm"
                            onClick={() => setExpandedControl(isExpanded ? null : `${assessment.framework}-${assessment.control_id}`)}
                          >
                            <td className="px-4 py-3 text-slate-300 whitespace-nowrap">{assessment.framework}</td>
                            <td className="px-4 py-3 text-white font-medium">{assessment.control_id}</td>
                            <td className="px-4 py-3 text-slate-300 truncate max-w-sm" title={assessment.control_title}>
                              {assessment.control_title}
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs border ${getStatusColor(assessment.status)}`}>
                                {getStatusIcon(assessment.status)}
                                {assessment.status.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right text-slate-300">
                              {(assessment.confidence * 100).toFixed(0)}%
                            </td>
                            <td className="px-4 py-3 text-right">
                              {isExpanded ? (
                                <ChevronUp className="w-5 h-5 text-slate-400 inline" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-slate-400 inline" />
                              )}
                            </td>
                          </tr>
                          
                          {/* Evidence Drawer */}
                          {isExpanded && (
                            <tr className="bg-slate-900/95 border-l-2 border-l-cyber-cyan">
                              <td colSpan={6} className="p-0">
                                <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                                  
                                  <div className="lg:col-span-2 space-y-4">
                                    {assessment.evidence_quote ? (
                                      <div>
                                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Evidence Quote</h4>
                                        <p className="text-sm text-slate-300 bg-black/30 p-4 rounded-lg border border-border/50 italic leading-relaxed">
                                          "{assessment.evidence_quote}"
                                        </p>
                                      </div>
                                    ) : (
                                      <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-lg flex gap-3 text-sm text-amber-200">
                                        <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-400" />
                                        <p>
                                          {assessment.gap_reason || "No sufficient policy evidence was found to assess this control."}
                                        </p>
                                      </div>
                                    )}
                                    
                                    {assessment.explanation && (
                                      <div>
                                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">AI Explanation</h4>
                                        <p className="text-sm text-slate-300">{assessment.explanation}</p>
                                      </div>
                                    )}
                                  </div>
                                  
                                  <div className="space-y-4">
                                    <div>
                                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Source Document</h4>
                                      {assessment.source_url ? (
                                        <a 
                                          href={assessment.source_url} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          className="text-sm text-cyber-cyan hover:text-white flex items-center gap-1 transition-colors"
                                        >
                                          <ExternalLink className="w-4 h-4" />
                                          View Original Policy
                                        </a>
                                      ) : (
                                        <span className="text-sm text-slate-500">Not available</span>
                                      )}
                                    </div>
                                    
                                    {assessment.gap_reason && assessment.status !== 'NOT_ASSESSED' && (
                                      <div>
                                        <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1">Gap Reason</h4>
                                        <p className="text-sm text-slate-300">{assessment.gap_reason}</p>
                                      </div>
                                    )}
                                  </div>

                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Note banner */}
            <div className="bg-slate-900/50 p-4 border-t border-border flex gap-3 items-start">
              <Info className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-slate-400">
                <strong className="text-white">Note:</strong> The crosswalk is an evidence-based policy assessment, NOT a certification verification system. Policy evidence indicates the control is satisfied based on available documentation. It does not certify that the vendor operates the control effectively in practice.
              </p>
            </div>
          </div>
        </>
      ) : (
        <div className="glass-panel p-12 rounded-xl border border-border text-center">
          <p className="text-slate-400">Failed to load compliance data.</p>
        </div>
      )}
    </div>
  );
};
