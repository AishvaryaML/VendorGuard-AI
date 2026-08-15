import React from 'react';
import { PageHeader } from '../../components/common/PageHeader';
import { Bot, Send, Sparkles } from 'lucide-react';

export const AssistantPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <PageHeader
        title="VendorGuard AI Risk Assistant"
        description="Autonomous RAG conversational assistant grounded in extracted vendor policies and document embeddings."
      />

      <div className="glass-panel rounded-xl border border-border flex flex-col h-[500px]">
        <div className="p-4 border-b border-border flex items-center justify-between bg-surface/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-white flex items-center gap-2">
                Vendor Knowledge Base RAG Bot
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  <Sparkles className="w-2.5 h-2.5 inline mr-1" /> Vector Grounded
                </span>
              </div>
              <div className="text-[10px] text-slate-400">pgvector embedding search active</div>
            </div>
          </div>
        </div>

        <div className="flex-1 p-6 flex flex-col items-center justify-center text-center">
          <Bot className="w-12 h-12 text-cyber-cyan mb-3 opacity-60" />
          <h4 className="text-base font-semibold text-white">Ask VendorGuard AI Anything</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            "Does Vendor X sell customer data to 3rd parties?" or "Summarize SLA breach penalties in Vendor Y's Terms of Service."
          </p>
        </div>

        <div className="p-4 border-t border-border bg-surface/30">
          <div className="relative">
            <input
              type="text"
              placeholder="Type your question about vendor risk or document policies..."
              className="w-full pl-4 pr-12 py-2.5 bg-slate-900 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan"
            />
            <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-cyber-cyan text-black rounded-md hover:opacity-90">
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
