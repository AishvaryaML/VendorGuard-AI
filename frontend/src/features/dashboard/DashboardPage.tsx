import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../../components/common/PageHeader';
import {
  Building2,
  ShieldAlert,
  Activity,
  Bell,
  TrendingUp,
  AlertTriangle,
  Loader2,
  ChevronRight,
  Clock,
  Bot,
  MessageSquareText,
  Sparkles,
} from 'lucide-react';
import { vendorApi, alertsApi } from '../../services/api';
import { Vendor, Alert, RiskTier } from '../../types';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  // Query Vendors
  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Query Alerts
  const { data: alertResponse, isLoading: isLoadingAlerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsApi.listAlerts({ limit: 10 }),
  });

  const alerts = alertResponse?.items || [];

  // Compute Metrics
  const totalVendors = vendors.length;
  const highCriticalCount = vendors.filter(
    (v) => v.risk_tier === 'High' || v.risk_tier === 'Critical'
  ).length;
  const activeAlertsCount = alerts.filter((a) => !a.is_read).length;
  const activeMonitoringCount = vendors.filter((v) => v.status === 'Active').length;

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
        title="Executive Security Dashboard"
        description="Continuous third-party vendor risk intelligence, real-time posture metrics, and AI multi-agent workflows."
        badge="Live System"
      />

      {/* Quick Action Bar for RAG Assistant & Agentic Workflows */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col sm:flex-row items-center justify-between gap-4 bg-gradient-to-r from-purple-950/20 via-surface to-cyber-cyan/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">AI Risk Intelligence Quick Actions</h4>
            <p className="text-xs text-slate-400">Ask questions using vector RAG or execute LangGraph multi-agent assessments.</p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={() => navigate('/assistant')}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2 bg-purple-500/20 text-purple-300 border border-purple-500/40 rounded-lg text-xs font-semibold hover:bg-purple-500/30 transition-colors"
          >
            <MessageSquareText className="w-4 h-4" /> Launch RAG Assistant
          </button>
          <button
            onClick={() => navigate('/vendors')}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black rounded-lg text-xs font-bold hover:opacity-90 transition-opacity"
          >
            <Bot className="w-4 h-4" /> Run Multi-Agent Workflow
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Monitored Vendors</span>
            <Building2 className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">{totalVendors}</span>
            <span className="text-xs font-medium text-cyber-cyan">Live API</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Active vendor profiles in database</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>High/Critical Risk</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">{highCriticalCount}</span>
            <span className="text-xs font-medium text-rose-400 flex items-center">
              <TrendingUp className="w-3 h-3 mr-1" />
              {totalVendors > 0 ? ((highCriticalCount / totalVendors) * 100).toFixed(0) : 0}%
            </span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Vendors exceeding risk threshold</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Continuous Monitoring</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">{activeMonitoringCount}</span>
            <span className="text-xs font-medium text-amber-400">Scheduled Engine</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Automated re-crawl tasks active</p>
        </div>

        <div className="glass-panel p-5 rounded-xl border border-border">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Active Alerts</span>
            <Bell className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-3xl font-bold text-white">{activeAlertsCount}</span>
            <span className="text-xs font-medium text-emerald-400">Unread</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2">Policy changes & degradation events</p>
        </div>
      </div>

      {/* Main Grid: Vendor Overview + Recent Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monitored Vendors Overview */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Building2 className="w-5 h-5 text-cyber-cyan" /> Registered Vendors Overview
            </h3>
            <button
              onClick={() => navigate('/vendors')}
              className="text-xs text-cyber-cyan hover:underline flex items-center gap-1"
            >
              Manage Catalog <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {isLoadingVendors ? (
            <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-cyber-cyan" /> Loading vendor profiles...
            </div>
          ) : vendors.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs space-y-2">
              <p>No vendors registered yet.</p>
              <button
                onClick={() => navigate('/vendors')}
                className="px-3 py-1.5 bg-cyber-cyan text-black font-semibold rounded text-xs"
              >
                Add First Vendor
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {vendors.slice(0, 5).map((v) => (
                <div
                  key={v.id}
                  onClick={() => navigate('/vendors')}
                  className="p-3 rounded-lg bg-slate-900/80 border border-border hover:border-cyber-cyan/50 cursor-pointer transition-colors flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-white">{v.name}</div>
                    <div className="text-[11px] text-slate-400 font-mono">{v.domain}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-0.5 rounded-full border text-[10px] font-bold ${getTierBadge(v.risk_tier)}`}>
                      {v.risk_tier} ({v.current_risk_score.toFixed(1)})
                    </span>
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Security Alerts Feed */}
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-amber-400" /> Live Alert Feed
            </h3>
            <button
              onClick={() => navigate('/alerts')}
              className="text-xs text-cyber-cyan hover:underline flex items-center gap-1"
            >
              View All ({alerts.length}) <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {isLoadingAlerts ? (
            <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-amber-400" /> Loading alert feed...
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              <AlertTriangle className="w-8 h-8 text-amber-400/50 mx-auto mb-2" />
              No active security or policy change alerts.
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 4).map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => navigate('/alerts')}
                  className={`p-3 rounded-lg border text-xs cursor-pointer transition-colors ${
                    alert.is_read
                      ? 'bg-slate-900/50 border-border/50 opacity-70'
                      : 'bg-amber-500/10 border-amber-500/30'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-white">{alert.title}</span>
                    <span className="text-[10px] text-amber-400 font-semibold">{alert.severity}</span>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1 line-clamp-2">{alert.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
