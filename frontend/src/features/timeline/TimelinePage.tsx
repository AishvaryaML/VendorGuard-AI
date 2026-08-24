import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import { History, Building2, FileText, Sparkles, Bell, Clock, Loader2 } from 'lucide-react';
import { vendorApi, alertsApi } from '../../services/api';
import { Vendor, Alert } from '../../types';

interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'VENDOR' | 'DOCUMENT' | 'ASSESSMENT' | 'ALERT';
  title: string;
  description: string;
  vendorName: string;
}

export const TimelinePage: React.FC = () => {
  // Fetch Vendors
  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Fetch Alerts
  const { data: alertResponse, isLoading: isLoadingAlerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsApi.listAlerts({ limit: 100 }),
  });

  const alerts = alertResponse?.items || [];

  // Build Chronological Event List from real backend data
  const events: TimelineEvent[] = [];

  vendors.forEach((v) => {
    // 1. Vendor Created Event
    events.push({
      id: `v-created-${v.id}`,
      timestamp: v.created_at,
      type: 'VENDOR',
      title: `Vendor Registered: ${v.name}`,
      description: `Initial profile created for ${v.domain} (${v.website_url}). Initial crawling initiated.`,
      vendorName: v.name,
    });

    // 2. Document & Policy Version Events
    v.documents?.forEach((doc) => {
      doc.versions?.forEach((ver) => {
        events.push({
          id: `ver-${ver.id}`,
          timestamp: ver.crawled_at,
          type: 'DOCUMENT',
          title: `Policy Version v${ver.version_number}: ${doc.document_type}`,
          description: ver.change_summary || ver.summary || `SHA-256 Hash: ${ver.content_hash.slice(0, 12)}...`,
          vendorName: v.name,
        });
      });
    });

    // 3. Risk Assessment Events
    if (v.current_risk_score > 0) {
      events.push({
        id: `assessment-${v.id}`,
        timestamp: v.last_monitored_at || v.updated_at,
        type: 'ASSESSMENT',
        title: `AI Risk Assessment Completed: ${v.name}`,
        description: `Overall Risk Score: ${v.current_risk_score.toFixed(1)} (${v.risk_tier} Risk Tier).`,
        vendorName: v.name,
      });
    }
  });

  // 4. Alert Events
  alerts.forEach((a) => {
    const v = vendors.find((vendor) => vendor.id === a.vendor_id);
    events.push({
      id: `alert-${a.id}`,
      timestamp: a.created_at,
      type: 'ALERT',
      title: a.title,
      description: a.description,
      vendorName: v ? v.name : 'Vendor',
    });
  });

  // Sort descending by timestamp
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const getEventIcon = (type: TimelineEvent['type']) => {
    switch (type) {
      case 'VENDOR':
        return <Building2 className="w-4 h-4 text-cyber-cyan" />;
      case 'DOCUMENT':
        return <FileText className="w-4 h-4 text-purple-400" />;
      case 'ASSESSMENT':
        return <Sparkles className="w-4 h-4 text-emerald-400" />;
      case 'ALERT':
        return <Bell className="w-4 h-4 text-amber-400" />;
    }
  };

  const isLoading = isLoadingVendors || isLoadingAlerts;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Temporal Policy & Risk Timeline"
        description="Historical risk trajectory analysis, document version comparison, and audit events."
      />

      {isLoading ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
          <p className="text-sm text-slate-400">Aggregating temporal risk trajectory timeline...</p>
        </div>
      ) : events.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl border border-border text-center flex flex-col items-center justify-center min-h-[350px]">
          <History className="w-12 h-12 text-purple-400/50 mb-4" />
          <h3 className="text-xl font-bold text-white">No Timeline Events Recorded</h3>
          <p className="text-sm text-slate-400 max-w-md mt-2">
            Register vendors and run policy assessments to record temporal trajectory snapshots.
          </p>
        </div>
      ) : (
        <div className="glass-panel p-6 rounded-xl border border-border space-y-6">
          <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-border pb-3">
            <History className="w-5 h-5 text-purple-400" /> Audit & Policy Change Trajectory ({events.length} Events)
          </h3>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
            {events.map((event) => (
              <div key={event.id} className="relative flex items-start gap-4">
                <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-slate-900 border border-border flex items-center justify-center">
                  {getEventIcon(event.type)}
                </div>

                <div className="p-4 rounded-xl bg-slate-900/90 border border-border w-full space-y-1">
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <span className="font-bold text-white text-xs">{event.title}</span>
                    <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" /> {new Date(event.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300">{event.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
