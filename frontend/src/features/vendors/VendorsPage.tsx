import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Building2, Plus, Search, Filter } from 'lucide-react';

export const VendorsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Management Directory"
        description="Centralized third-party vendor catalog with discovery tools, document tracking, and risk tiering."
        action={
          <button className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyber-cyan to-cyber-blue text-black font-semibold text-xs rounded-lg hover:opacity-90 transition-opacity">
            <Plus className="w-4 h-4" /> Add Vendor Profile
          </button>
        }
      />

      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search vendor domain or name..."
            className="w-full pl-9 pr-4 py-2 bg-slate-900/90 border border-border rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
          />
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button className="flex items-center gap-2 px-3 py-2 bg-surface border border-border rounded-lg text-xs text-slate-300 hover:text-white">
            <Filter className="w-3.5 h-3.5" /> Filter Tier
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-xl border border-border p-12 text-center flex flex-col items-center justify-center min-h-[350px]">
        <div className="w-16 h-16 rounded-2xl bg-cyber-blue/10 border border-cyber-blue/30 flex items-center justify-center text-cyber-blue mb-4">
          <Building2 className="w-8 h-8" />
        </div>
        <h3 className="text-xl font-bold text-white">Vendor Catalog Initialization Ready</h3>
        <p className="text-sm text-slate-400 max-w-md mt-2">
          The database schema and API structure are configured. Vendor management models and web crawling discovery will be active in Phase 2.
        </p>
      </div>
    </div>
  );
};
