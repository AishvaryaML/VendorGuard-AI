import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  Bell,
  CheckCheck,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  Building2,
  Clock,
} from 'lucide-react';
import { alertsApi, vendorApi } from '../../services/api';
import { Alert, Vendor, RiskTier } from '../../types';

export const AlertsPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [selectedVendorId, setSelectedVendorId] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
  const [readFilter, setReadFilter] = useState<string>('ALL'); // ALL, unread, read

  // Fetch Vendors for dropdown
  const { data: vendors = [] } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Query Alerts with Filters
  const { data: alertResponse, isLoading, isError } = useQuery({
    queryKey: ['alerts', selectedVendorId, selectedType, selectedSeverity, readFilter],
    queryFn: () => {
      const params: any = {};
      if (selectedVendorId !== 'ALL') params.vendor_id = selectedVendorId;
      if (selectedType !== 'ALL') params.alert_type = selectedType;
      if (selectedSeverity !== 'ALL') params.severity = selectedSeverity;
      if (readFilter === 'unread') params.is_read = false;
      if (readFilter === 'read') params.is_read = true;
      return alertsApi.listAlerts(params);
    },
  });

  const alerts = alertResponse?.items || [];

  // Mark Read Mutation
  const markReadMutation = useMutation({
    mutationFn: (alertId: string) => alertsApi.markAsRead(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  // Mark All Read Handler
  const handleMarkAllRead = async () => {
    const unreadAlerts = alerts.filter((a) => !a.is_read);
    for (const alert of unreadAlerts) {
      await alertsApi.markAsRead(alert.id);
    }
    queryClient.invalidateQueries({ queryKey: ['alerts'] });
  };

  const getSeverityBadge = (severity: RiskTier | string) => {
    switch (severity) {
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

  const getVendorName = (vendorId: string) => {
    const v = vendors.find((v) => v.id === vendorId);
    return v ? v.name : 'Vendor';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security & Policy Change Alerts"
        description="Real-time notifications for policy modifications, risk score drops, and news/threat events."
        action={
          <button
            onClick={handleMarkAllRead}
            disabled={alerts.filter((a) => !a.is_read).length === 0}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border text-slate-300 hover:text-white font-medium text-xs rounded-lg disabled:opacity-50"
          >
            <CheckCheck className="w-3.5 h-3.5 text-emerald-400" /> Mark All as Read
          </button>
        }
      />

      {/* Filter Bar */}
      <div className="glass-panel p-4 rounded-xl border border-border grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div>
          <label className="block text-slate-400 font-medium mb-1">Filter Vendor</label>
          <select
            value={selectedVendorId}
            onChange={(e) => setSelectedVendorId(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">All Vendors</option>
            {vendors.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-slate-400 font-medium mb-1">Filter Alert Type</label>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">All Alert Types</option>
            <option value="Policy Change">Policy Change</option>
            <option value="Risk Degradation">Risk Degradation</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 font-medium mb-1">Filter Severity</label>
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">All Severities</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 font-medium mb-1">Read Status</label>
          <select
            value={readFilter}
            onChange={(e) => setReadFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-900 border border-border rounded-lg text-white focus:outline-none focus:border-cyber-cyan"
          >
            <option value="ALL">All Statuses</option>
            <option value="unread">Unread Only</option>
            <option value="read">Read Only</option>
          </select>
        </div>
      </div>

      {/* Alerts Feed List */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-amber-400 animate-spin mb-3" />
          <p className="text-sm text-slate-400">Loading alerts feed...</p>
        </div>
      ) : isError || alerts.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-4">
            <Bell className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-white">No Security Alerts Found</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            No policy change or risk degradation alerts match the selected criteria.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border transition-colors space-y-2 ${
                alert.is_read
                  ? 'bg-slate-900/40 border-border/60 opacity-80'
                  : 'bg-slate-900/90 border-amber-500/40 shadow-lg shadow-amber-500/5'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase bg-surface text-cyber-cyan border border-cyber-cyan/30">
                    {alert.alert_type}
                  </span>
                  <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(alert.severity)}`}>
                    {alert.severity} Severity
                  </span>
                  <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
                    <Building2 className="w-3.5 h-3.5 text-slate-500" /> {getVendorName(alert.vendor_id)}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {new Date(alert.created_at).toLocaleString()}
                  </span>
                  {!alert.is_read ? (
                    <button
                      onClick={() => markReadMutation.mutate(alert.id)}
                      disabled={markReadMutation.isPending}
                      className="px-2.5 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30 rounded text-[11px] font-medium flex items-center gap-1"
                    >
                      <CheckCheck className="w-3 h-3" /> Mark Read
                    </button>
                  ) : (
                    <span className="text-[10px] text-slate-500 font-medium">Read</span>
                  )}
                </div>
              </div>

              <h4 className="text-sm font-bold text-white">{alert.title}</h4>
              <p className="text-xs text-slate-300 leading-relaxed">{alert.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
