import React, { useState } from 'react';
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
} from 'lucide-react';
import { vendorApi, riskApi } from '../../services/api';
import { Vendor, VendorCreate, RiskTier, MonitoringFrequency } from '../../types';

export const VendorsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [searchQuery, setSearchQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

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
        msg = detail
          .map((item: any) => item?.msg || JSON.stringify(item))
          .join(', ');
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Management Directory"
        description="Centralized third-party vendor catalog with discovery tools, document tracking, and risk tiering."
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

      {/* Action Success / Error Notifications */}
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

      {/* Filter and Search Bar */}
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
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${tierFilter === tier
                  ? 'bg-cyber-cyan/20 text-cyber-cyan border-cyber-cyan/50'
                  : 'bg-surface border-border text-slate-400 hover:text-white'
                }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {/* Vendor Table List */}
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
          <div className="w-16 h-16 rounded-2xl bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center text-cyber-blue mb-4">
            <Building2 className="w-8 h-8" />
          </div>
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
                      <button
                        onClick={() => analyzeVendorMutation.mutate(vendor.id)}
                        disabled={analyzeVendorMutation.isPending}
                        className="px-3 py-1.5 bg-gradient-to-r from-cyber-cyan/20 to-cyber-blue/20 text-cyber-cyan border border-cyber-cyan/40 hover:bg-cyber-cyan/30 rounded-lg text-xs font-medium disabled:opacity-50"
                      >
                        {analyzeVendorMutation.isPending && analyzeVendorMutation.variables === vendor.id ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 inline mr-1 animate-spin" /> Analyzing...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3.5 h-3.5 inline mr-1" /> Run AI Assessment
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

      {/* Selected Vendor Detail Drawer / Modal */}
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
