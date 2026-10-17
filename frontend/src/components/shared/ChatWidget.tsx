import { useState, useRef, useEffect } from "react";
import { X, Send, ChevronDown } from "lucide-react";
import { ChakraIcon } from "./ChakraIcon";
import { StatusBadge } from "./Badges";
import { trackComplaint } from "@/api/client";
import type { CivicIssue } from "@/types";
import { cn } from "@/lib/utils";

interface Msg {
  from: "user" | "bot";
  text?: string;
  issue?: CivicIssue;
  chips?: string[];
  loading?: boolean;
}

const QUICK_CHIPS = [
  "Track by ID",
  "How long will it take?",
  "Report new issue",
];

const BOT_GREET: Msg = {
  from: "bot",
  text: "Namaste! 🙏 I'm the CivicFix Assistant. I can help you track a complaint or answer questions about Pune civic services.",
  chips: QUICK_CHIPS,
};

async function botReply(userText: string): Promise<Msg[]> {
  const low = userText.toLowerCase().trim();

  // Track by ID
  const idMatch = low.match(/cf-\d{4}-\d+/i) ?? userText.match(/CF-\d{4}-\d+/);
  if (idMatch) {
    const ref = idMatch[0].toUpperCase().startsWith("CF") ? idMatch[0].toUpperCase() : userText;
    const issue = await trackComplaint(ref);
    if (issue) {
      return [{ from: "bot", issue, text: `Here's the latest on **${issue.id}**:` }];
    }
    return [{ from: "bot", text: `I couldn't find complaint "${ref}". Please double-check your reference ID (format: CF-2026-000123).` }];
  }

  if (low.includes("track") || low.includes("status") || low.includes("id")) {
    return [{ from: "bot", text: "Please share your complaint reference ID (e.g. CF-2026-000123) and I'll pull it up.", chips: [] }];
  }
  if (low.includes("how long") || low.includes("time") || low.includes("eta")) {
    return [{ from: "bot", text: "Average resolution time in Pune is 4–7 days depending on category. Critical issues are prioritised within 24 hours.", chips: QUICK_CHIPS }];
  }
  if (low.includes("report") || low.includes("new")) {
    return [{ from: "bot", text: "To report a new issue, tap the big orange 'Report Issue' button in the menu or visit /report.", chips: [] }];
  }

  return [{ from: "bot", text: "I'm not sure about that yet. You can track a complaint by sharing its ID, or contact PMC helpline at 020-25506800.", chips: QUICK_CHIPS }];
}

interface ChatWidgetProps {
  embedded?: boolean;
  initialRef?: string;
}

export function ChatWidget({ embedded = false, initialRef }: ChatWidgetProps) {
  const [open, setOpen] = useState(embedded);
  const [msgs, setMsgs] = useState<Msg[]>([BOT_GREET]);
  const [input, setInput] = useState(initialRef ?? "");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setInput("");
    setMsgs((m) => [...m, { from: "user", text }, { from: "bot", loading: true }]);
    setBusy(true);
    try {
      const replies = await botReply(text);
      setMsgs((m) => [...m.filter((x) => !x.loading), ...replies]);
    } finally {
      setBusy(false);
    }
  }

  const panel = (
    <div className={cn("flex flex-col bg-white rounded-2xl overflow-hidden shadow-2xl",
      embedded ? "w-full" : "w-80 sm:w-96 h-[480px]")}>
      {/* Header */}
      <div className="bg-navy flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <ChakraIcon size={22} color="white" />
          <div>
            <p className="text-white font-heading font-semibold text-sm leading-tight">CivicFix Assistant</p>
            <p className="text-navy-50/70 text-[11px]">PMC · Pune</p>
          </div>
        </div>
        {!embedded && (
          <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white" aria-label="Close chat">
            <X size={18} />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3 bg-gray-50">
        {msgs.map((m, i) => (
          <div key={i} className={cn("flex", m.from === "user" ? "justify-end" : "justify-start")}>
            {m.from === "bot" && !m.loading && (
              <span className="w-6 h-6 bg-navy rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 mr-2">
                <ChakraIcon size={14} color="white" />
              </span>
            )}
            <div className={cn("max-w-[85%]", m.from === "user" ? "ml-auto" : "")}>
              {m.loading ? (
                <div className="bubble-bot px-3 py-2 flex items-center gap-2">
                  <ChakraIcon size={14} color="#000080" spinning />
                  <span className="text-xs text-gray-500">Thinking…</span>
                </div>
              ) : m.issue ? (
                <div className="bubble-bot p-3 text-sm">
                  {m.text && <p className="text-navy-900 mb-2 font-medium">{m.text}</p>}
                  <IssueSnippet issue={m.issue} />
                </div>
              ) : (
                <div className={cn("px-3 py-2 text-sm text-navy-900 leading-relaxed",
                  m.from === "user" ? "bubble-user" : "bubble-bot")}>
                  {m.text}
                </div>
              )}
              {m.chips && m.chips.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {m.chips.map((c) => (
                    <button
                      key={c}
                      onClick={() => send(c)}
                      className="text-xs bg-white border border-navy/20 text-navy px-2.5 py-1 rounded-badge hover:bg-navy-50 transition-colors"
                    >
                      {c}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={(e) => { e.preventDefault(); send(input); }}
        className="flex items-center gap-2 px-3 py-3 border-t border-gray-100 bg-white"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a reference ID or question…"
          className="flex-1 text-sm border border-gray-200 rounded-input px-3 py-2 focus:outline-none focus:ring-2 focus:ring-navy/40 bg-gray-50"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="w-9 h-9 bg-saffron text-navy-900 rounded-full flex items-center justify-center hover:bg-saffron-dark transition-colors disabled:opacity-40"
          aria-label="Send message"
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );

  if (embedded) return panel;

  return (
    <>
      {/* Floating bubble */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-navy rounded-full shadow-xl flex items-center justify-center hover:bg-navy/90 transition-all active:scale-95 focus-visible:ring-2 focus-visible:ring-saffron"
        aria-label="Open CivicFix chat assistant"
        style={{ bottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))" }}
      >
        {open ? (
          <ChevronDown size={24} className="text-white" />
        ) : (
          <ChakraIcon size={28} color="#FF9933" />
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-40" style={{ bottom: "calc(5.5rem + env(safe-area-inset-bottom, 0px))" }}>
          {panel}
        </div>
      )}
    </>
  );
}

function IssueSnippet({ issue }: { issue: CivicIssue }) {
  return (
    <div className="bg-white rounded-card p-2 border border-gray-100 space-y-1.5">
      <div className="flex items-center gap-1.5 flex-wrap">
        <StatusBadge status={issue.status} />
        <span className="text-xs text-gray-400">#{issue.id}</span>
      </div>
      <p className="font-semibold text-navy-900 text-xs leading-snug">{issue.title}</p>
      <p className="text-[11px] text-gray-500">{issue.address}</p>
      <p className="text-[11px] text-gray-400">Team: {issue.team} · ETA: {issue.eta}</p>
    </div>
  );
}
