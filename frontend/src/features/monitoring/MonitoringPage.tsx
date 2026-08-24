import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  Activity,
  Play,
  RefreshCw,
  Clock,
  Building2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  FileCheck,
  Bell,
} from 'lucide-react';
import { vendorApi, monitoringApi } from '../../services/api';
import { Vendor, MonitoringTriggerResponse } from '../../types';

export const MonitoringPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [triggerResult, setTriggerResult] = useState<MonitoringTriggerResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch Vendors Catalog
  const { data: vendors = [], isLoading, isError } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Trigger Monitoring Mutation
  const triggerMutation = useMutation({
    mutationFn: (vendorId?: string) => monitoringApi.triggerMonitoring(vendorId, true),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['monitoring-status'] });
      setTriggerResult(res);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to trigger monitoring cycle.';
      setErrorMessage(msg);
    },
  });

  const handleTriggerAll = () => {
    setTriggerResult(null);
    setErrorMessage(null);
    triggerMutation.mutate(undefined);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Continuous Monitoring Engine"
        description="Automated background schedule monitoring, SHA-256 policy change verification, and delta risk recalculation."
        action={
          <button
            onClick={handleTriggerAll}
            disabled={triggerMutation.isPending || vendors.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-surface border border-cyber-cyan/40 text-cyber-cyan font-semibold text-xs rounded-lg hover:bg-cyber-cyan/10 transition-colors disabled:opacity-50"
          >
            {triggerMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Monitoring Active...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" /> Trigger Immediate Monitor Cycle
              </>
            )}
          </button>
        }
      />

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Trigger Results Summary Modal / Dialog */}
      {triggerResult && (
        <div className="p-5 rounded-xl bg-slate-900 border border-cyber-cyan/40 space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2 text-cyber-cyan font-bold text-sm">
              <CheckCircle2 className="w-4 h-4" /> Monitoring Cycle Completed
            </div>
            <button onClick={() => setTriggerResult(null)} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-slate-300">{triggerResult.message}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {triggerResult.results.map((r) => (
              <div key={r.vendor_id} className="p-3 rounded bg-surface border border-border space-y-1">
                <div className="font-semibold text-white justify-between flex">
                  <span>{r.vendor_name}</span>
                  <span className={r.status === 'Success' ? 'text-emerald-400' : 'text-rose-400'}>{r.status}</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Docs Checked: {r.documents_checked} | Docs Changed: {r.documents_changed}
                </div>
                <div className="text-[11px] text-slate-400">
                  Risk Reassessed: {r.risk_reassessed ? 'Yes' : 'No'} | Alerts: {r.alerts_generated}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Active Scheduler Status</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">APScheduler Active</div>
          <p className="text-xs text-slate-500 mt-1">Python background worker integrated in FastAPI</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Monitored Vendors</span>
            <Clock className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{vendors.length} Profiles</div>
          <p className="text-xs text-slate-500 mt-1">Daily / Weekly / Monthly intervals</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="text-xs text-slate-400 font-medium flex items-center justify-between">
            <span>Change Engine</span>
            <RefreshCw className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">SHA-256 Hashing</div>
          <p className="text-xs text-slate-500 mt-1">Unified text diffing & risk reassessment</p>
        </div>
      </div>

      {/* Monitored Vendors Status List */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-cyber-cyan animate-spin mb-3" />
          <p className="text-sm text-slate-400">Loading monitoring schedule status...</p>
        </div>
      ) : isError || vendors.length === 0 ? (
        <div className="glass-panel rounded-xl border border-border p-12 text-center flex flex-col items-center justify-center min-h-[300px]">
          <Activity className="w-12 h-12 text-cyber-cyan/50 mb-4" />
          <h3 className="text-xl font-bold text-white">No Vendors Configured for Monitoring</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Register third-party vendors in the Vendors Directory to activate continuous background monitoring.
          </p>
        </div>
      ) : (
        <div className="glass-panel rounded-xl border border-border p-6 space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-border pb-3">
            <Building2 className="w-5 h-5 text-cyber-cyan" /> Vendor Monitoring Schedule Status
          </h3>

          <div className="grid grid-cols-1 gap-3">
            {vendors.map((vendor) => (
              <div
                key={vendor.id}
                className="p-4 rounded-xl bg-slate-900/90 border border-border flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-xs"
              >
                <div className="space-y-1">
                  <div className="font-bold text-white text-sm flex items-center gap-2">
                    {vendor.name}
                    <span className="px-2 py-0.5 rounded text-[10px] bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30">
                      {vendor.monitoring_frequency} Interval
                    </span>
                  </div>
                  <div className="text-slate-400 font-mono">{vendor.domain} ({vendor.website_url})</div>
                  <div className="text-slate-500 text-[11px] flex items-center gap-3">
                    <span>Last Crawled: {vendor.last_monitored_at ? new Date(vendor.last_monitored_at).toLocaleString() : 'Never'}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
                  <div className="text-right">
                    <span className="text-[11px] text-slate-400 block">Risk Score</span>
                    <span className="font-bold text-white">{vendor.current_risk_score.toFixed(1)} ({vendor.risk_tier})</span>
                  </div>
                  <button
                    onClick={() => triggerMutation.mutate(vendor.id)}
                    disabled={triggerMutation.isPending}
                    className="px-3 py-2 bg-surface border border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/20 rounded-lg font-semibold flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {triggerMutation.isPending && triggerMutation.variables === vendor.id ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Monitoring...
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" /> Monitor Now
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
