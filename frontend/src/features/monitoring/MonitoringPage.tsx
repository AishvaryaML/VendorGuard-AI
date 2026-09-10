import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { vendorApi, monitoringApi } from '../../services/api';
import { Vendor, MonitoringJobStatusResponse } from '../../types';

export const MonitoringPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [dismissedJobId, setDismissedJobId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch Vendors Catalog
  const { data: vendors = [], isLoading, isError } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Poll Background Monitoring Job Status every 2 seconds while pending or running
  const { data: activeJob } = useQuery<MonitoringJobStatusResponse>({
    queryKey: ['monitoring-job', activeJobId],
    queryFn: () => monitoringApi.getJobStatus(activeJobId!),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const st = query.state.data?.status;
      return (st === 'pending' || st === 'running') ? 2000 : false;
    },
  });

  // Refresh data when job completes
  useEffect(() => {
    if (activeJob?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['monitoring-status'] });
    }
  }, [activeJob?.status, queryClient]);

  // Trigger Monitoring Mutation
  const triggerMutation = useMutation({
    mutationFn: (vendorId?: string) => monitoringApi.triggerMonitoring(vendorId, true),
    onSuccess: (res) => {
      setActiveJobId(res.job_id);
      setDismissedJobId(null);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to trigger monitoring cycle.';
      setErrorMessage(msg);
    },
  });

  const handleTriggerAll = () => {
    setErrorMessage(null);
    triggerMutation.mutate(undefined);
  };

  const isJobRunning = activeJob?.status === 'pending' || activeJob?.status === 'running' || triggerMutation.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Continuous Monitoring Engine"
        description="Automated background schedule monitoring, SHA-256 policy change verification, and delta risk recalculation."
        action={
          <button
            onClick={handleTriggerAll}
            disabled={isJobRunning || vendors.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-surface border border-cyber-cyan/40 text-cyber-cyan font-semibold text-xs rounded-lg hover:bg-cyber-cyan/10 transition-colors disabled:opacity-50"
          >
            {isJobRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Monitoring in Progress...
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

      {/* Active Job Progress Card (Live Polling) */}
      {activeJob && activeJob.job_id !== dismissedJobId && (
        <>
          {(activeJob.status === 'pending' || activeJob.status === 'running') && (
            <div className="p-5 rounded-xl bg-slate-900/90 border border-cyber-cyan/50 shadow-lg shadow-cyber-cyan/5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center">
                    <RefreshCw className="w-4 h-4 text-cyber-cyan animate-spin" />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      Continuous Monitoring in Progress
                      <span className="px-2 py-0.5 rounded text-[10px] bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/40 uppercase font-mono">
                        {activeJob.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {activeJob.total_vendors === 0
                        ? 'Checking vendor monitoring schedules...'
                        : `Scanning vendor ${Math.min(activeJob.completed_vendors + 1, activeJob.total_vendors)} of ${activeJob.total_vendors}`}
                    </p>
                  </div>
                </div>
                <div className="text-right text-xs">
                  <span className="text-slate-400">Job ID: </span>
                  <span className="font-mono text-cyber-cyan">{activeJob.job_id.slice(0, 8)}...</span>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-border">
                <div
                  className="bg-gradient-to-r from-cyber-cyan to-blue-500 h-full transition-all duration-500 rounded-full"
                  style={{
                    width: `${activeJob.total_vendors > 0 ? (activeJob.completed_vendors / activeJob.total_vendors) * 100 : 15}%`,
                  }}
                />
              </div>

              <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pt-1">
                <div>
                  <span className="text-slate-500">Current Vendor: </span>
                  <span className="font-medium text-white">{activeJob.current_vendor || 'Initializing pipeline...'}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-emerald-400">✓ {activeJob.successful_vendors} Successful</span>
                  <span className="text-rose-400">✗ {activeJob.failed_vendors} Failed</span>
                </div>
              </div>
            </div>
          )}

          {activeJob.status === 'completed' && (
            <div className="p-5 rounded-xl bg-slate-900/90 border border-emerald-500/40 shadow-lg shadow-emerald-500/5 space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Monitoring Completed
                </div>
                <button
                  onClick={() => setDismissedJobId(activeJob.job_id)}
                  className="text-slate-400 hover:text-white transition-colors"
                  title="Dismiss"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {activeJob.total_vendors === 0 ? (
                <p className="text-xs text-slate-300">
                  Zero vendors currently due for scheduled monitoring. All vendor policy documents are up-to-date.
                </p>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-slate-300">
                    Continuous monitoring cycle executed successfully across all target vendor profiles.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <div className="text-[11px] text-slate-400">Vendors Processed</div>
                      <div className="text-lg font-bold text-white mt-0.5">
                        {activeJob.completed_vendors} / {activeJob.total_vendors}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <div className="text-[11px] text-emerald-400">Successful</div>
                      <div className="text-lg font-bold text-emerald-400 mt-0.5">{activeJob.successful_vendors}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-surface border border-border">
                      <div className="text-[11px] text-rose-400">Failed</div>
                      <div className="text-lg font-bold text-rose-400 mt-0.5">{activeJob.failed_vendors}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeJob.status === 'failed' && (
            <div className="p-5 rounded-xl bg-slate-900/90 border border-rose-500/40 space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
                  <AlertCircle className="w-5 h-5 text-rose-400" /> Monitoring Job Failed
                </div>
                <button
                  onClick={() => setDismissedJobId(activeJob.job_id)}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-rose-300">
                {activeJob.error || 'An unrecoverable failure occurred during background monitoring.'}
              </p>
            </div>
          )}
        </>
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
            {vendors.map((vendor) => {
              const isThisVendorCurrent = isJobRunning && activeJob?.current_vendor === vendor.name;
              return (
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
                      {isThisVendorCurrent && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 animate-pulse">
                          <Loader2 className="w-3 h-3 animate-spin" /> Scanning now
                        </span>
                      )}
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
                      disabled={isJobRunning}
                      className="px-3 py-2 bg-surface border border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/20 rounded-lg font-semibold flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {isThisVendorCurrent ? (
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
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
