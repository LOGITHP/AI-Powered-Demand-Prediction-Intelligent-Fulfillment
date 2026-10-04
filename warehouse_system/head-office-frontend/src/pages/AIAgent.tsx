import { useEffect, useRef, useState } from 'react';
import {
  Activity, Bot, CheckCircle2, Clock, Send, Wrench, XCircle, User as UserIcon, History,
} from 'lucide-react';
import api from '../lib/api';
import type { ChatMessage, Decision } from '../lib/api';

const SUGGESTIONS = [
  'Which warehouses need attention right now?',
  'Simulate a 20% demand increase at WH-001',
  'Where are the worker shortages and surpluses?',
  'Move 5 workers from WH-EAST to WH-NORTH to cover the spike',
];

function DecisionCard({
  decision, onResolve, resolving,
}: {
  decision: Decision;
  onResolve: (id: string, approved: boolean) => void;
  resolving: boolean;
}) {
  return (
    <div className="p-5 border border-gray-100 bg-white rounded-xl shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-100 text-amber-800 mb-2">
            <Clock className="w-3.5 h-3.5" /> Awaiting Approval
          </span>
          <h3 className="font-bold text-gray-900">{decision.event.replace(/_/g, ' ')}</h3>
          <p className="text-gray-600 mt-1 text-sm">{decision.recommendation}</p>
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {new Date(decision.timestamp).toLocaleTimeString()}
        </span>
      </div>

      {decision.reasoning?.length > 0 && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
          <p className="font-semibold mb-2 text-sm text-gray-800 flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-amber-500" /> Reasoning
          </p>
          <ul className="list-disc pl-5 space-y-1 text-sm text-gray-600">
            {decision.reasoning.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      <div className="mt-4 flex gap-3 border-t border-gray-100 pt-4">
        <button
          disabled={resolving}
          onClick={() => decision.decision_id && onResolve(decision.decision_id, true)}
          className="px-5 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
        >
          Approve & Execute
        </button>
        <button
          disabled={resolving}
          onClick={() => decision.decision_id && onResolve(decision.decision_id, false)}
          className="px-5 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Decline
        </button>
      </div>
    </div>
  );
}

export default function AIAgent() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'I monitor the whole warehouse network. Ask me about live state, risks, shortages, or run what-if demand simulations. Operational changes I propose always require your approval.',
    },
  ]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [pending, setPending] = useState<Decision[]>([]);
  const [history, setHistory] = useState<Decision[]>([]);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const refreshDecisions = async () => {
    try {
      const res = await api.get<Decision[]>('/decisions');
      const all = res.data;
      setPending(all.filter((d) => d.status === 'PENDING_APPROVAL'));
      setHistory(all.filter((d) => d.status !== 'PENDING_APPROVAL').slice(0, 8));
    } catch (e) {
      console.error('Failed to fetch decisions', e);
    }
  };

  useEffect(() => {
    refreshDecisions();
    const interval = setInterval(refreshDecisions, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  const sendQuery = async (text?: string) => {
    const query = (text ?? input).trim();
    if (!query || thinking) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: query }]);
    setThinking(true);
    try {
      const res = await api.post('/query', { query });
      setMessages((m) => [...m, { role: 'assistant', content: res.data.response, toolsUsed: res.data.tools_used }]);
      refreshDecisions(); // the agent may have created a proposal
    } catch (e) {
      console.error('Query failed', e);
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Failed to reach the agent service. Check that the Head Office agent is running.' },
      ]);
    } finally {
      setThinking(false);
    }
  };

  const handleApprove = async (decisionId: string, approved: boolean) => {
    setResolvingId(decisionId);
    try {
      await api.post('/approve', {
        decision_id: decisionId,
        approved,
        reason: approved ? undefined : 'Manager declined the decision manually',
      });
      await refreshDecisions();
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: approved
            ? `Decision ${decisionId} approved. Execution result dispatched to the warehouse.`
            : `Decision ${decisionId} declined. No changes were applied.`,
        },
      ]);
    } catch (e) {
      console.error('Failed to submit approval', e);
      alert('Failed to communicate with AI orchestrator');
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">AI Agent Orchestrator</h1>
          <p className="text-sm text-gray-500 mt-1">
            Grounded in live network state - every tool call is shown inline
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Chat panel */}
        <div className="xl:col-span-3 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col h-[620px]">
          <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/50 rounded-t-2xl flex items-center gap-2">
            <Bot className="w-5 h-5 text-indigo-500" />
            <h2 className="font-semibold text-gray-900">Network Agent</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-indigo-600" />
                  </div>
                )}
                <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-md'
                    : 'bg-gray-100 text-gray-800 rounded-tl-md'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {msg.toolsUsed.map((t, j) => (
                        <span key={j} className="inline-flex items-center gap-1 text-[11px] font-medium bg-white border border-indigo-200 text-indigo-700 px-2 py-0.5 rounded-full">
                          <Wrench className="w-3 h-3" /> {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                    <UserIcon className="w-4 h-4 text-gray-600" />
                  </div>
                )}
              </div>
            ))}
            {thinking && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="bg-gray-100 rounded-2xl rounded-tl-md px-4 py-3 flex gap-1.5 items-center">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="text-xs text-gray-500 ml-2">inspecting network tools…</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="border-t border-gray-100 p-4">
            <div className="flex flex-wrap gap-2 mb-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendQuery(s)}
                  disabled={thinking}
                  className="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 px-3 py-1.5 rounded-full transition-colors disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
            <form
              onSubmit={(e) => { e.preventDefault(); sendQuery(); }}
              className="flex gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about the network, or request a reallocation…"
                className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <button
                type="submit"
                disabled={thinking || !input.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 rounded-xl transition-colors disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Decisions panel */}
        <div className="xl:col-span-2 space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/50 flex items-center justify-between">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <Activity className="w-5 h-5 text-indigo-500" /> Pending Decisions
              </h2>
              {pending.length > 0 && (
                <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2 py-1 rounded-full">
                  {pending.length}
                </span>
              )}
            </div>
            <div className="p-5 space-y-4 max-h-[420px] overflow-y-auto">
              {pending.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle2 className="w-8 h-8 text-emerald-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No decisions awaiting approval.</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Ask the agent to reallocate workers to create one.
                  </p>
                </div>
              ) : (
                pending.map((d) => (
                  <DecisionCard
                    key={d.decision_id}
                    decision={d}
                    onResolve={handleApprove}
                    resolving={resolvingId === d.decision_id}
                  />
                ))
              )}
            </div>
          </div>

          {history.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 bg-gray-50/50">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <History className="w-5 h-5 text-gray-400" /> Recent Decisions
                </h2>
              </div>
              <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto">
                {history.map((d, i) => (
                  <div key={d.decision_id ?? i} className="px-5 py-3 flex items-start gap-3">
                    {d.status === 'APPROVED' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">{d.recommendation}</p>
                      <p className="text-xs text-gray-400">
                        {d.status} · {new Date(d.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
