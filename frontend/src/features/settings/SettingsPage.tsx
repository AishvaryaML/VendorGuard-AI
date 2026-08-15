import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Settings, Key, Database, Shield, Sliders } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="System Settings & API Configurations"
        description="Environment parameters, API keys, database connection status, and monitoring frequency defaults."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border text-white font-semibold text-sm">
            <Database className="w-4 h-4 text-cyber-cyan" /> Database Connection
          </div>
          <div className="text-xs space-y-2">
            <div className="flex justify-between text-slate-400">
              <span>Database Engine:</span>
              <span className="text-slate-200 font-mono">PostgreSQL / SQLite</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Vector Search Extension:</span>
              <span className="text-emerald-400 font-medium">pgvector Ready</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>ORM Layer:</span>
              <span className="text-slate-200 font-mono">SQLAlchemy 2.0 Async</span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-border space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border text-white font-semibold text-sm">
            <Key className="w-4 h-4 text-purple-400" /> AI LLM Configuration
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
              <span>Framework:</span>
              <span className="text-cyber-cyan font-medium">LangChain / LangGraph</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
