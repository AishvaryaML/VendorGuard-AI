import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import { Settings, Key, Database, Shield, Sliders, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { healthApi } from '../../services/api';
import { SystemHealth } from '../../types';

export const SettingsPage: React.FC = () => {
  const { data: health, isLoading, isError } = useQuery<SystemHealth>({
    queryKey: ['health'],
    queryFn: () => healthApi.checkHealth(),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Settings & API Configurations"
        description="Environment parameters, API keys, database connection status, and monitoring frequency defaults."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend API Health Status */}
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-border text-white font-semibold text-sm">
            <div className="flex items-center gap-3">
              <Shield className="w-4 h-4 text-cyber-cyan" /> FastAPI Backend Engine
            </div>
            {isLoading ? (
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin text-cyber-cyan" /> Checking...
              </span>
            ) : isError ? (
              <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> Disconnected
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Healthy
              </span>
            )}
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>App Name:</span>
              <span className="text-slate-200 font-semibold">{health?.app_name || 'VendorGuard AI'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Environment:</span>
              <span className="text-cyber-cyan font-mono">{health?.environment || 'development'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>API V1 Base URL:</span>
              <span className="text-slate-200 font-mono">/api/v1</span>
            </div>
          </div>
        </div>

        {/* Database & ORM Status */}
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border text-white font-semibold text-sm">
            <Database className="w-4 h-4 text-cyber-cyan" /> Database Connection
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>Database Engine:</span>
              <span className="text-slate-200 font-mono">SQLite (aiosqlite) / PostgreSQL</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Async Driver:</span>
              <span className="text-emerald-400 font-medium font-mono">aiosqlite 0.20.0</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>ORM Layer:</span>
              <span className="text-slate-200 font-mono">SQLAlchemy 2.0.35 Async</span>
            </div>
          </div>
        </div>

        {/* AI LLM Configuration */}
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border text-white font-semibold text-sm">
            <Key className="w-4 h-4 text-purple-400" /> AI LLM Risk Engine Configuration
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>LLM Model:</span>
              <span className="text-slate-200 font-mono">gpt-4o-mini</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Embeddings:</span>
              <span className="text-slate-200 font-mono">text-embedding-3-small</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Provider SDK:</span>
              <span className="text-cyber-cyan font-medium">AsyncOpenAI 3.1.0</span>
            </div>
          </div>
        </div>

        {/* Scheduler Configuration */}
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border text-white font-semibold text-sm">
            <Sliders className="w-4 h-4 text-amber-400" /> Continuous Monitoring Scheduler
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>Engine:</span>
              <span className="text-slate-200 font-mono">APScheduler 3.11.3</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Lifespan Integration:</span>
              <span className="text-emerald-400 font-medium">FastAPI lifespan (AsyncIO)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Frequencies:</span>
              <span className="text-slate-200 font-mono">Daily (24h) / Weekly (7d) / Monthly (30d)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
