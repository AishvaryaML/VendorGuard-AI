import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  Building2,
  Plus,
  Search,
  Filter,
  ExternalLink,
  ShieldAlert,
  Clock,
  FileText,
  Loader2,
  X,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Eye,
  Bot,
  Check,
  UserCheck,
  AlertTriangle,
} from 'lucide-react';
import { vendorApi, riskApi, agenticApi } from '../../services/api';
import {
  Vendor,
  VendorCreate,
  RiskTier,
  MonitoringFrequency,
  WorkflowStatusResponse,
} from '../../types';

export const VendorsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Workflow Modal State
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowStatusResponse | null>(null);
  const [isWorkflowModalOpen, setIsWorkflowModalOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState<string>('');
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Form State
  const [formData, setFormData] = useState<VendorCreate>({
    name: '',
    website_url: '',
    industry: '',
    monitoring_frequency: 'Daily',
  });

  // Query Vendors
  const { data: vendors = [], isLoading, isError, error } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Query Selected Vendor Documents
  const { data: selectedVendorDocs = [], isLoading: isLoadingDocs } = useQuery({
    queryKey: ['vendor-documents', selectedVendor?.id],
    queryFn: () => (selectedVendor ? vendorApi.getVendorDocuments(selectedVendor.id) : Promise.resolve([])),
    enabled: !!selectedVendor,
  });

  // Clean up polling interval
  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  // Poll workflow status
  const startPollingWorkflow = (workflowId: string) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const updated = await agenticApi.getWorkflowStatus(workflowId);
        setActiveWorkflow(updated);

        // Stop polling on terminal states or HITL interrupt gate
        if (
          updated.status === 'completed' ||
          updated.status === 'rejected' ||
          updated.status === 'failed' ||
          updated.status === 'awaiting_approval'
        ) {
          stopPolling();
          queryClient.invalidateQueries({ queryKey: ['vendors'] });
          queryClient.invalidateQueries({ queryKey: ['alerts'] });
        }
      } catch (err) {
        stopPolling();
      }
    }, 1500);
  };

  // Run Workflow Mutation
  const runWorkflowMutation = useMutation({
    mutationFn: (vendorId: string) => agenticApi.runWorkflow({ vendor_id: vendorId }),
    onSuccess: (initialState) => {
      setActiveWorkflow(initialState);
      setIsWorkflowModalOpen(true);
      setApprovalNotes('');

      // If workflow immediately finished or paused at HITL, no need to poll
      if (
        initialState.status === 'completed' ||
        initialState.status === 'rejected' ||
        initialState.status === 'failed' ||
        initialState.status === 'awaiting_approval'
      ) {
        queryClient.invalidateQueries({ queryKey: ['vendors'] });
      } else {
        startPollingWorkflow(initialState.workflow_id);
      }
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Multi-agent workflow execution failed.';
      setActionError(msg);
    },
  });

  // Approval Mutation
  const handleApprovalSubmit = async (approved: boolean) => {
    if (!activeWorkflow || isSubmittingApproval) return;

    setIsSubmittingApproval(true);
    setActionError(null);

    try {
      const result = await agenticApi.approveWorkflow(activeWorkflow.workflow_id, {
        approved,
        notes: approvalNotes.trim() || undefined,
      });

      setActiveWorkflow(result);
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });

      if (approved) {
        setActionSuccess(`Workflow for '${result.vendor_name}' approved and completed!`);
      } else {
        setActionSuccess(`Workflow for '${result.vendor_name}' rejected by analyst.`);
      }
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Approval decision submission failed.';
      setActionError(msg);
    } finally {
      setIsSubmittingApproval(false);
    }
  };

  // Create Vendor Mutation
  const createVendorMutation = useMutation({
    mutationFn: (newVendor: VendorCreate) => vendorApi.createVendor(newVendor),
    onSuccess: (newVendor) => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      setIsAddModalOpen(false);
      setFormData({ name: '', website_url: '', industry: '', monitoring_frequency: 'Daily' });
      setActionSuccess(`Vendor '${newVendor.name}' registered and initial documents discovered!`);
      setSelectedVendor(newVendor);
      setTimeout(() => setActionSuccess(null), 5000);
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      let msg = 'Failed to create vendor and crawl website.';

      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((item: any) => item?.msg || JSON.stringify(item)).join(', ');
      } else if (detail && typeof detail === 'object') {
        msg = detail.msg || JSON.stringify(detail);
      } else if (err.message) {
        msg = err.message;
      }

      setActionError(msg);
    },
  });

  // Analyze Vendor Mutation
  const analyzeVendorMutation = useMutation({
    mutationFn: (vendorId: string) => riskApi.analyzeVendor(vendorId),
    onSuccess: (assessment) => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['risk-assessment', assessment.vendor_id] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setActionSuccess(`AI Risk Assessment completed! Overall Score: ${assessment.overall_score} (${assessment.risk_tier})`);
      setTimeout(() => setActionSuccess(null), 5000);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Risk assessment failed.';
      setActionError(msg);
    },
  });

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);

    if (!formData.name.trim() || !formData.website_url.trim()) {
      setActionError('Vendor Name and Website URL are required.');
      return;
    }

    let url = formData.website_url.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }

    createVendorMutation.mutate({
      ...formData,
      website_url: url,
    });
  };

  const filteredVendors = vendors.filter((v) => {
    const matchesSearch =
      v.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      v.domain.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTier = tierFilter === 'ALL' || v.risk_tier === tierFilter;
    return matchesSearch && matchesTier;
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

  // Helper for Stepper Progress
  const stepperNodes = [
    { key: 'discovery', label: 'Discovery', description: 'Crawl policy docs' },
    { key: 'policy_audit', label: 'Policy Audit', description: 'RAG chunking & vector indexing' },
    { key: 'risk_audit', label: 'Risk Audit', description: 'Deterministic Risk Engine analysis' },
    { key: 'human_approval', label: 'HITL Evaluator', description: 'Gating threshold check' },
    { key: 'executive_report', label: 'Executive Report', description: 'Summary & Alert synthesis' },
  ];

  const getStepStatus = (stepKey: string, currentStep: string, workflowStatus: string) => {
    if (workflowStatus === 'failed') return 'failed';

    const stepOrder = ['start', 'discovery', 'policy_audit', 'risk_audit', 'human_approval', 'executive_report', 'completed'];
    const currIdx = stepOrder.indexOf(currentStep);
    const stepIdx = stepOrder.indexOf(stepKey);

    if (workflowStatus === 'completed') return 'completed';
    if (workflowStatus === 'awaiting_approval' && stepKey === 'human_approval') return 'awaiting';
    if (currIdx > stepIdx) return 'completed';
    if (currIdx === stepIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Management Directory"
        description="Centralized third-party vendor catalog with discovery tools, document tracking, and LangGraph multi-agent intelligence."
        action={
          <button
            onClick={() => {
              setActionError(null);
              setIsAddModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-semibold text-xs rounded-lg hover:opacity-90 transition-opacity shadow-lg shadow-cyber-cyan/10"
          >
            <Plus className="w-4 h-4" /> Add Vendor Profile
          </button>
        }
      />

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search vendor domain or name..."
            className="w-full pl-9 pr-4 py-2 bg-slate-900/90 border border-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <span className="text-xs text-slate-400 flex items-center gap-1 mr-2">
            <Filter className="w-3.5 h-3.5" /> Risk Tier:
          </span>
          {['ALL', 'Low', 'Medium', 'High', 'Critical'].map((tier) => (
            <button
              key={tier}
              onClick={() => setTierFilter(tier)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                tierFilter === tier
                  ? 'bg-cyber-cyan/20 text-cyber-cyan border-cyber-cyan/50'
                  : 'bg-surface border-border text-slate-400 hover:text-white'
              }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {/* Catalog Table */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-cyber-cyan animate-spin mb-3" />
          <p className="text-sm text-slate-400">Loading vendor catalog from backend...</p>
        </div>
      ) : isError ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <AlertCircle className="w-8 h-8 text-rose-400 mb-3" />
          <h3 className="text-base font-semibold text-white">Error Connecting to Backend API</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md">
            {(error as any)?.message || 'Ensure the FastAPI backend is running on http://localhost:8000'}
          </p>
        </div>
      ) : filteredVendors.length === 0 ? (
        <div className="glass-panel rounded-xl border border-border p-12 text-center flex flex-col items-center justify-center min-h-[350px]">
          <Building2 className="w-12 h-12 text-cyber-blue/50 mb-4" />
          <h3 className="text-xl font-bold text-white">No Vendors Registered</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Add a vendor website URL to initiate initial document discovery and AI risk assessment.
          </p>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="mt-5 px-4 py-2 bg-cyber-cyan text-black font-semibold text-xs rounded-lg hover:opacity-90"
          >
            Add First Vendor
          </button>
        </div>
      ) : (
        <div className="glass-panel rounded-xl border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-surface/80 uppercase text-[11px] text-slate-400 tracking-wider border-b border-border">
                <tr>
                  <th className="p-4">Vendor Name</th>
                  <th className="p-4">Domain</th>
                  <th className="p-4">Risk Tier</th>
                  <th className="p-4">Risk Score</th>
                  <th className="p-4">Monitoring Frequency</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {filteredVendors.map((vendor) => (
                  <tr key={vendor.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="p-4 font-semibold text-white flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-cyber-cyan" />
                      {vendor.name}
                    </td>
                    <td className="p-4 font-mono text-slate-400">
                      <a
                        href={vendor.website_url}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:text-cyber-cyan flex items-center gap-1"
                      >
                        {vendor.domain} <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                    <td className="p-4">
                      <span className={`px-2.5 py-1 rounded-full border text-[11px] font-semibold ${getTierBadge(vendor.risk_tier)}`}>
                        {vendor.risk_tier}
                      </span>
                    </td>
                    <td className="p-4 font-bold text-white">
                      <span className={vendor.current_risk_score >= 50 ? 'text-rose-400' : 'text-emerald-400'}>
                        {vendor.current_risk_score.toFixed(1)} / 100
                      </span>
                    </td>
                    <td className="p-4 text-slate-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-500" /> {vendor.monitoring_frequency}
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {vendor.status}
                      </span>
                    </td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => setSelectedVendor(vendor)}
                        className="px-3 py-1.5 bg-surface border border-border text-slate-300 hover:text-white rounded-lg text-xs font-medium hover:border-cyber-cyan"
                      >
                        <Eye className="w-3.5 h-3.5 inline mr-1" /> Details
                      </button>

                      {/* Run Multi-Agent Workflow Button */}
                      <button
                        onClick={() => runWorkflowMutation.mutate(vendor.id)}
                        disabled={runWorkflowMutation.isPending}
                        className="px-3 py-1.5 bg-gradient-to-r from-purple-500/20 to-cyber-cyan/20 text-purple-300 border border-purple-500/40 hover:bg-purple-500/30 rounded-lg text-xs font-semibold disabled:opacity-50"
                      >
                        {runWorkflowMutation.isPending && runWorkflowMutation.variables === vendor.id ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Executing Agents...
                          </>
                        ) : (
                          <>
                            <Bot className="w-3.5 h-3.5 inline mr-1" /> Run Agentic Workflow
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Multi-Agent Workflow & HITL Modal */}
      {isWorkflowModalOpen && activeWorkflow && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="glass-panel border border-border rounded-xl max-w-3xl w-full p-6 space-y-6 relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => {
                stopPolling();
                setIsWorkflowModalOpen(false);
                setActiveWorkflow(null);
              }}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Title */}
            <div className="border-b border-border pb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    LangGraph Multi-Agent Workflow
                  </h3>
                  <p className="text-xs text-slate-400">
                    Vendor: <span className="text-white font-semibold">{activeWorkflow.vendor_name}</span> ({activeWorkflow.domain})
                  </p>
                </div>
              </div>
              <span className="text-xs font-mono text-slate-400">ID: {activeWorkflow.workflow_id.slice(0, 8)}...</span>
            </div>

            {/* Stepper Progress */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Workflow Agent Execution Pipeline</h4>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
                {stepperNodes.map((st) => {
                  const status = getStepStatus(st.key, activeWorkflow.current_step, activeWorkflow.status);
                  return (
                    <div
                      key={st.key}
                      className={`p-3 rounded-lg border text-center space-y-1 transition-all ${
                        status === 'completed'
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                          : status === 'active'
                          ? 'bg-cyber-cyan/20 border-cyber-cyan text-cyber-cyan animate-pulse'
                          : status === 'awaiting'
                          ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                          : status === 'failed'
                          ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                          : 'bg-surface/50 border-border text-slate-500'
                      }`}
                    >
                      <div className="flex items-center justify-center gap-1 font-bold text-xs">
                        {status === 'completed' && <Check className="w-3.5 h-3.5" />}
                        {status === 'active' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        {status === 'awaiting' && <AlertTriangle className="w-3.5 h-3.5" />}
                        <span>{st.label}</span>
                      </div>
                      <p className="text-[10px] text-slate-400 line-clamp-1">{st.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* HITL Approval Panel (If status === 'awaiting_approval') */}
            {activeWorkflow.status === 'awaiting_approval' && (
              <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/40 space-y-4">
                <div className="flex items-center gap-3 text-amber-400 border-b border-amber-500/30 pb-3">
                  <UserCheck className="w-6 h-6 flex-shrink-0" />
                  <div>
                    <h4 className="text-base font-bold text-white">Human Analyst Approval Required</h4>
                    <p className="text-xs text-amber-300 mt-0.5">
                      Risk Tier evaluated to <span className="font-bold uppercase">{activeWorkflow.risk_tier}</span> (Score: {activeWorkflow.overall_score.toFixed(1)}). Workflow paused at HITL gate.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-3 rounded bg-slate-900 border border-border">
                    <span className="text-slate-400 block font-semibold">Overall Risk Score</span>
                    <span className="text-2xl font-bold text-rose-400 mt-1 block">
                      {activeWorkflow.overall_score.toFixed(1)} / 100
                    </span>
                  </div>
                  <div className="p-3 rounded bg-slate-900 border border-border">
                    <span className="text-slate-400 block font-semibold">Indexed Chunks</span>
                    <span className="text-2xl font-bold text-cyber-cyan mt-1 block">
                      {activeWorkflow.indexed_chunks_count} Vectors
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs">
                  <label className="block text-slate-300 font-semibold">Analyst Notes (Optional)</label>
                  <textarea
                    value={approvalNotes}
                    onChange={(e) => setApprovalNotes(e.target.value)}
                    placeholder="Enter justification or instructions before approving/rejecting..."
                    rows={2}
                    className="w-full p-2.5 bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={() => handleApprovalSubmit(false)}
                    disabled={isSubmittingApproval}
                    className="px-4 py-2 bg-rose-500/20 text-rose-300 border border-rose-500/40 rounded-lg text-xs font-bold hover:bg-rose-500/30 disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {isSubmittingApproval ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                    Reject Assessment
                  </button>
                  <button
                    onClick={() => handleApprovalSubmit(true)}
                    disabled={isSubmittingApproval}
                    className="px-4 py-2 bg-emerald-500 text-black rounded-lg text-xs font-bold hover:opacity-90 disabled:opacity-50 flex items-center gap-1.5 shadow-lg shadow-emerald-500/20"
                  >
                    {isSubmittingApproval ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                    Approve Assessment
                  </button>
                </div>
              </div>
            )}

            {/* Executive Summary Output (If Completed or Rejected) */}
            {(activeWorkflow.status === 'completed' || activeWorkflow.status === 'rejected') && (
              <div className="p-5 rounded-xl bg-slate-900 border border-border space-y-3">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <h4 className="text-xs font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-cyber-cyan" /> Executive Summary & Findings
                  </h4>
                  <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold ${
                    activeWorkflow.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                  }`}>
                    {activeWorkflow.status.toUpperCase()}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {activeWorkflow.executive_summary || 'Workflow completed. Risk score updated in vendor catalog.'}
                </p>

                {activeWorkflow.approval_notes && (
                  <div className="p-2.5 rounded bg-surface border border-border text-[11px] text-slate-400 font-mono">
                    Analyst Note: "{activeWorkflow.approval_notes}"
                  </div>
                )}
              </div>
            )}

            {/* Footer */}
            <div className="border-t border-border pt-4 flex justify-between items-center text-xs">
              <span className="text-slate-400 font-mono">Status: <span className="text-white font-bold">{activeWorkflow.status}</span></span>
              <button
                onClick={() => {
                  stopPolling();
                  setIsWorkflowModalOpen(false);
                  setActiveWorkflow(null);
                }}
                className="px-4 py-2 bg-surface border border-border text-slate-300 hover:text-white font-semibold rounded-lg"
              >
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Vendor Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-panel border border-border rounded-xl max-w-md w-full p-6 space-y-4 relative">
            <button
              onClick={() => setIsAddModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 border-b border-border pb-3">
              <Building2 className="w-5 h-5 text-cyber-cyan" />
              <h3 className="text-lg font-bold text-white">Add New Vendor Profile</h3>
            </div>

            <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Vendor Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Stripe, Slack, AWS"
                  className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Website URL *</label>
                <input
                  type="url"
                  required
                  value={formData.website_url}
                  onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                  placeholder="https://vendor.com"
                  className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  VendorGuard crawler will automatically discover Privacy, Terms, Security, and Compliance pages.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Industry (Optional)</label>
                <input
                  type="text"
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  placeholder="e.g. FinTech, Cloud SaaS, Security"
                  className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Monitoring Frequency</label>
                <select
                  value={formData.monitoring_frequency}
                  onChange={(e) => setFormData({ ...formData, monitoring_frequency: e.target.value as MonitoringFrequency })}
                  className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
                >
                  <option value="Daily">Daily (24h)</option>
                  <option value="Weekly">Weekly (7d)</option>
                  <option value="Monthly">Monthly (30d)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 bg-surface border border-border text-slate-300 hover:text-white rounded-lg font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createVendorMutation.isPending}
                  className="px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-bold rounded-lg hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {createVendorMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Crawling & Registering...
                    </>
                  ) : (
                    'Add Vendor'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Vendor Details Drawer / Modal */}
      {selectedVendor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="glass-panel border border-border rounded-xl max-w-2xl w-full p-6 space-y-5 relative max-h-[85vh] overflow-y-auto">
            <button
              onClick={() => setSelectedVendor(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="border-b border-border pb-4 flex justify-between items-start">
              <div>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-cyber-cyan" /> {selectedVendor.name}
                </h3>
                <a
                  href={selectedVendor.website_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-cyber-cyan hover:underline flex items-center gap-1 mt-1 font-mono"
                >
                  {selectedVendor.website_url} <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full border text-xs font-bold ${getTierBadge(selectedVendor.risk_tier)}`}>
                  {selectedVendor.risk_tier} Risk ({selectedVendor.current_risk_score.toFixed(1)})
                </span>
              </div>
            </div>

            {/* Document Discovery List */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyber-cyan" /> Discovered Policy Documents ({selectedVendorDocs.length})
              </h4>

              {isLoadingDocs ? (
                <div className="p-6 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-cyber-cyan" /> Loading documents...
                </div>
              ) : selectedVendorDocs.length === 0 ? (
                <div className="p-4 rounded-lg bg-surface border border-border text-center text-xs text-slate-400">
                  No policy documents discovered yet. Re-crawl or trigger risk assessment.
                </div>
              ) : (
                <div className="space-y-2">
                  {selectedVendorDocs.map((doc) => (
                    <div key={doc.id} className="p-3 rounded-lg bg-slate-900/80 border border-border flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-slate-200">{doc.document_type} - {doc.title}</div>
                        <a href={doc.url} target="_blank" rel="noreferrer" className="text-[11px] text-slate-400 hover:text-cyber-cyan font-mono truncate max-w-md block">
                          {doc.url}
                        </a>
                      </div>
                      <div className="text-right text-[10px] text-slate-400 font-mono">
                        <div>Hash: {doc.current_version_hash?.slice(0, 10)}...</div>
                        {doc.last_crawled_at && (
                          <div className="text-slate-500">Crawled: {new Date(doc.last_crawled_at).toLocaleDateString()}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="border-t border-border pt-4 flex justify-between items-center">
              <button
                onClick={() => analyzeVendorMutation.mutate(selectedVendor.id)}
                disabled={analyzeVendorMutation.isPending}
                className="px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-bold text-xs rounded-lg hover:opacity-90 flex items-center gap-2 disabled:opacity-50"
              >
                {analyzeVendorMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> AI Analyzing Policies...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" /> Run AI Risk Assessment
                  </>
                )}
              </button>
              <button
                onClick={() => setSelectedVendor(null)}
                className="px-4 py-2 bg-surface border border-border text-slate-300 hover:text-white text-xs font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VendorsPage;
