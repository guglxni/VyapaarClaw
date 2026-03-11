"use client";

import { useState, useRef, useEffect } from "react";
import { AppShell } from "../components/shell";
import {
  Send,
  Shield,
  Bot,
  User,
  Loader2,
} from "lucide-react";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content: `Welcome. I'm your AI CFO — VyapaarClaw.

I can help you with:
- **Evaluate payouts** — run the full governance pipeline on a proposed payment
- **Check agent budgets** — see who's spending what and how much headroom remains
- **Vendor due diligence** — verify vendor reputation and legal entity status
- **Compliance reports** — generate governance summaries for any period
- **Forecast cash flow** — project budget burn rates and exhaustion dates
- **Investigate anomalies** — dig into flagged transactions

Connect me to the OpenClaw gateway to enable live tool execution. For now, this chat interface shows how the conversation flows.

What would you like to review?`,
  timestamp: new Date(),
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    setTimeout(() => {
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: getContextualResponse(userMsg.content),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setSending(false);
    }, 800 + Math.random() * 1200);
  };

  return (
    <AppShell>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[var(--color-border)] px-6 py-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[var(--color-accent)]" />
            <h1 className="text-sm font-semibold">Chat with AI CFO</h1>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
              VyapaarClaw
            </span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
            >
              {msg.role === "assistant" && (
                <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-[var(--color-accent)]" />
                </div>
              )}
              <div
                className={`max-w-[600px] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[var(--color-accent)]/10 text-[var(--color-text)]"
                    : "bg-[var(--color-surface)] border border-[var(--color-border)]"
                }`}
              >
                <div className="whitespace-pre-wrap">
                  {msg.content.split(/(\*\*.*?\*\*)/).map((part, i) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <strong key={i}>{part.slice(2, -2)}</strong>
                    ) : (
                      <span key={i}>{part.replace(/^- /gm, "\u2022 ")}</span>
                    )
                  )}
                </div>
                <div className="text-[10px] text-[var(--color-text-dim)] mt-2">
                  {msg.timestamp.toLocaleTimeString("en-IN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
              </div>
              {msg.role === "user" && (
                <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
                  <User className="w-4 h-4 text-[var(--color-text-muted)]" />
                </div>
              )}
            </div>
          ))}
          {sending && (
            <div className="flex gap-3">
              <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-[var(--color-accent)]/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-[var(--color-accent)]" />
              </div>
              <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin text-[var(--color-accent)]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex-shrink-0 border-t border-[var(--color-border)] p-4">
          <div className="flex gap-2 max-w-[800px] mx-auto">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
              placeholder="Ask the AI CFO anything..."
              className="flex-1 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-2.5 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] focus:outline-none focus:border-[var(--color-accent)]/50"
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || sending}
              className="px-4 py-2.5 bg-[var(--color-accent)] text-black rounded-lg text-sm font-medium hover:bg-[var(--color-accent-dim)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function getContextualResponse(input: string): string {
  const lower = input.toLowerCase();
  if (lower.includes("budget") || lower.includes("spend"))
    return `Here's the current budget status across agents:

**procurement-bot**: ₹3,200 / ₹5,000 (64%) — Yellow
**payroll-agent**: ₹18,000 / ₹25,000 (72%) — Yellow
**marketing-bot**: ₹150 / ₹1,000 (15%) — Green
**infra-agent**: ₹8,900 / ₹10,000 (89%) — RED

The infra-agent is critically close to its daily limit. I recommend either increasing its limit via \`set_agent_policy\` or investigating whether the current burn rate is expected.`;

  if (lower.includes("vendor") || lower.includes("reputation"))
    return `To check a vendor's trustworthiness, I would run:

1. \`check_vendor_reputation(url)\` — Google Safe Browsing threat check
2. \`verify_vendor_entity(name)\` — GLEIF legal entity verification
3. \`get_vendor_trust_score(url)\` — Historical trust score from audit logs

Provide a vendor URL or name and I'll run the full due diligence pipeline.`;

  if (lower.includes("compliance") || lower.includes("report"))
    return `The weekly compliance report for the last 7 days shows:

• **47 total decisions**: 38 approved, 6 rejected, 3 held
• **Approval rate**: 80.9% — within healthy range
• **Top rejection reason**: TXN_LIMIT_EXCEEDED (3 instances)
• **High-risk agent**: infra-agent (25% rejection rate)
• **Total volume**: ₹40,500

Recommendation: Review infra-agent's per-txn limit — it may be too low for their operational needs. The 3 held transactions are awaiting human review in Telegram.`;

  if (lower.includes("forecast") || lower.includes("cash flow"))
    return `Cash flow forecast based on 7-day history:

**procurement-bot**: Stable burn rate, ~₹3,000/day. Healthy.
**payroll-agent**: High but predictable. Budget headroom adequate.
**marketing-bot**: Low and decreasing. Well within limits.
**infra-agent**: INCREASING trend — was ₹5,000/day last week, now ₹8,900/day. At this rate, will hit daily limit within 1-2 hours each day.

Action item: Investigate infra-agent's spending increase. Consider promoting to Tier 3 if justified, or capping with a lower per-txn limit if anomalous.`;

  return `I can help with that. As the AI CFO, I have access to 25 governance tools covering:

• **Budget monitoring** — track spend, forecast burn, reallocate limits
• **Vendor verification** — reputation, entity, trust scoring
• **Risk assessment** — anomaly detection, transaction scoring
• **Compliance** — audit logs, governance reports, decision history
• **Human-in-the-loop** — Telegram/Slack approval workflows

What specific aspect would you like to explore?`;
}
