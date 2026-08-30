import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { PageHeader } from '../../components/common/PageHeader';
import {
  Bot,
  Send,
  Sparkles,
  Building2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2,
  FileText,
  AlertCircle,
  User,
  ShieldCheck,
} from 'lucide-react';
import { vendorApi, assistantApi } from '../../services/api';
import { Vendor, AssistantCitation, ChatMessagePayload } from '../../types';

interface MessageUI {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: AssistantCitation[];
}

export const AssistantPage: React.FC = () => {
  const [selectedVendorId, setSelectedVendorId] = useState<string>('');
  const [inputMessage, setInputMessage] = useState<string>('');
  const [messages, setMessages] = useState<MessageUI[]>([]);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const [apiError, setApiError] = useState<string | null>(null);

  // Fetch live vendor list
  const { data: vendors = [], isLoading: isLoadingVendors } = useQuery<Vendor[]>({
    queryKey: ['vendors'],
    queryFn: () => vendorApi.listVendors(),
  });

  // Auto-select first vendor when loaded if none selected
  const activeVendorId = selectedVendorId || (vendors.length > 0 ? vendors[0].id : '');
  const activeVendor = vendors.find((v) => v.id === activeVendorId);

  // Chat Mutation
  const chatMutation = useMutation({
    mutationFn: async (userPrompt: string) => {
      if (!activeVendorId) {
        throw new Error('Please select a vendor profile before sending your query.');
      }

      // Build stateless conversation history from previous turns
      const conversation_history: ChatMessagePayload[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      return assistantApi.chat({
        vendor_id: activeVendorId,
        message: userPrompt,
        conversation_history,
      });
    },
    onSuccess: (response, userPrompt) => {
      setApiError(null);
      const assistantMsg: MessageUI = {
        id: 'msg-' + Date.now(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(response.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    },
    onError: (err: any) => {
      let msg = err.response?.data?.detail || err.message || 'Assistant request failed.';
      if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
        msg = 'The AI Assistant request timed out (60s limit). Local Ollama inference may still be processing or loading the model. Please ensure Ollama is active (`ollama run llama3.2`) and try again.';
      } else if (err.message && err.message.toLowerCase().includes('network error')) {
        msg = 'Network error connecting to the backend API. Please ensure the VendorGuard backend server is running on port 8000.';
      }
      setApiError(msg);
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || chatMutation.isPending) return;

    const userText = inputMessage.trim();
    setInputMessage('');
    setApiError(null);

    const userMsg: MessageUI = {
      id: 'user-' + Date.now(),
      role: 'user',
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    chatMutation.mutate(userText);
  };

  const toggleSourceExpand = (sourceId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [sourceId]: !prev[sourceId],
    }));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="VendorGuard AI Risk Assistant"
        description="Autonomous RAG conversational assistant grounded in extracted vendor policies and document embeddings."
      />

      {/* Vendor Context Selector & Status */}
      <div className="glass-panel p-4 rounded-xl border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3 w-full md:w-auto">
          <Building2 className="w-5 h-5 text-cyber-cyan" />
          <span className="text-xs font-semibold text-white">Target Vendor Context:</span>
          {isLoadingVendors ? (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cyber-cyan" /> Loading vendors...
            </div>
          ) : (
            <select
              value={activeVendorId}
              onChange={(e) => {
                setSelectedVendorId(e.target.value);
                setMessages([]); // Clear previous chat context on vendor change
                setApiError(null);
              }}
              className="px-3 py-1.5 bg-slate-900 border border-border rounded-lg text-xs font-semibold text-white focus:outline-none focus:border-cyber-cyan"
            >
              {vendors.length === 0 ? (
                <option value="">No registered vendors found</option>
              ) : (
                vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.domain})
                  </option>
                ))
              )}
            </select>
          )}
        </div>

        {activeVendor && (
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <span className="px-2 py-0.5 rounded bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30">
              {activeVendor.risk_tier} Risk ({activeVendor.current_risk_score.toFixed(1)})
            </span>
            <span>{activeVendor.website_url}</span>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {apiError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{apiError}</span>
        </div>
      )}

      {/* Chat Container */}
      <div className="glass-panel rounded-xl border border-border flex flex-col h-[600px] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-surface/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-semibold text-white flex items-center gap-2">
                Vendor Knowledge Base RAG Bot
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1">
                  <Sparkles className="w-2.5 h-2.5 inline" /> Vector Grounded
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                Context Isolated: {activeVendor ? activeVendor.name : 'Select a Vendor'}
              </div>
            </div>
          </div>
        </div>

        {/* Message Feed */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Bot className="w-12 h-12 text-cyber-cyan mb-3 opacity-60" />
              <h4 className="text-base font-semibold text-white">Ask VendorGuard AI Anything</h4>
              <p className="text-xs text-slate-400 max-w-md mt-1">
                "Does {activeVendor?.name || 'this vendor'} sell customer personal data to 3rd parties?" or "Summarize security compliance standards."
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-xs ${
                  msg.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan flex-shrink-0">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-xl p-4 space-y-3 ${
                    msg.role === 'user'
                      ? 'bg-cyber-cyan/20 border border-cyber-cyan/40 text-white'
                      : 'bg-slate-900 border border-border text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-400 border-b border-border/50 pb-1 mb-1">
                    <span className="font-semibold">{msg.role === 'user' ? 'You' : 'VendorGuard Assistant'}</span>
                    <span>{msg.timestamp}</span>
                  </div>

                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                  {/* Grounded Citations List */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-3 border-t border-border/60 space-y-2">
                      <div className="text-[11px] font-bold text-cyber-cyan flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-cyber-cyan" /> Verified Policy Evidence ({msg.sources.length} Sources)
                      </div>

                      <div className="space-y-1.5">
                        {msg.sources.map((source, idx) => {
                          const sourceKey = `${msg.id}-src-${idx}`;
                          const isExpanded = !!expandedSources[sourceKey];

                          return (
                            <div key={sourceKey} className="p-2.5 rounded bg-surface/70 border border-border/70 space-y-1">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 font-semibold text-[11px] text-white">
                                  <FileText className="w-3 h-3 text-purple-400" />
                                  <span>{source.document_type}</span>
                                  <span className="text-[10px] text-slate-400">({source.title})</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] text-emerald-400 font-mono">
                                    {(source.similarity_score * 100).toFixed(1)}% match
                                  </span>
                                  <button
                                    onClick={() => toggleSourceExpand(sourceKey)}
                                    className="p-0.5 text-slate-400 hover:text-white"
                                  >
                                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                  </button>
                                </div>
                              </div>

                              <a
                                href={source.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-[10px] text-cyber-cyan hover:underline flex items-center gap-1 font-mono truncate"
                              >
                                {source.source_url} <ExternalLink className="w-2.5 h-2.5" />
                              </a>

                              {isExpanded && (
                                <div className="mt-2 p-2 rounded bg-slate-950 border border-border text-[11px] text-slate-300 font-mono whitespace-pre-wrap">
                                  "{source.snippet}"
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-lg bg-cyber-blue/20 border border-cyber-blue/40 flex items-center justify-center text-cyber-blue flex-shrink-0">
                    <User className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            ))
          )}

          {chatMutation.isPending && (
            <div className="flex gap-3 text-xs justify-start">
              <div className="w-7 h-7 rounded-lg bg-cyber-cyan/10 border border-cyber-cyan/30 flex items-center justify-center text-cyber-cyan flex-shrink-0">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-border text-slate-400 text-xs flex items-center gap-2">
                <span>RAG Retriever fetching vector evidence & constructing grounded prompt...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-4 border-t border-border bg-surface/30">
          <div className="relative">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={chatMutation.isPending || !activeVendorId}
              placeholder={
                activeVendor
                  ? `Ask a question about ${activeVendor.name}'s policies...`
                  : 'Please select a vendor to start chatting...'
              }
              className="w-full pl-4 pr-12 py-2.5 bg-slate-900 border border-border rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyber-cyan disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={chatMutation.isPending || !inputMessage.trim() || !activeVendorId}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-cyber-cyan text-black rounded-md hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {chatMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AssistantPage;
