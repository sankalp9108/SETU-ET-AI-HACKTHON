import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, MessageSquare } from "lucide-react";

import { useCopilotQuery } from "@/hooks/useCopilotQuery";
import { CitationList } from "@/components/CitationList";
import { ConfidenceBar } from "@/components/ConfidenceBar";
import { EmptyState } from "@/components/EmptyState";
import { ErrorBanner } from "@/components/ErrorBanner";
import type { CopilotQueryResponse } from "@/types/copilot";
import type { ApiError } from "@/api/client";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Copilot — SETU" },
      {
        name: "description",
        content:
          "Ask maintenance and operations questions in natural language. Answers cite the source documents.",
      },
    ],
  }),
  component: CopilotPage,
});

interface Turn {
  id: number;
  question: string;
  response?: CopilotQueryResponse;
  error?: ApiError;
  loading?: boolean;
}

function CopilotPage() {
  const mutation = useCopilotQuery();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns]);

  function ask() {
    const q = input.trim();
    if (!q || mutation.isPending) return;
    const id = Date.now();
    setTurns((t) => [...t, { id, question: q, loading: true }]);
    setInput("");
    mutation.mutate(q, {
      onSuccess: (response) => {
        setTurns((t) =>
          t.map((x) =>
            x.id === id ? { ...x, response, loading: false } : x,
          ),
        );
      },
      onError: (err) => {
        setTurns((t) =>
          t.map((x) =>
            x.id === id
              ? { ...x, error: err as ApiError, loading: false }
              : x,
          ),
        );
      },
    });
  }

  return (
    <div className="flex h-full min-h-[calc(100dvh-3.5rem)] flex-col md:min-h-[calc(100dvh-4rem)]">
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto px-4 py-6 md:px-8"
      >
        <div className="mx-auto max-w-3xl">
          {turns.length === 0 ? (
            <div className="mt-8">
              <div className="mb-6 flex items-center gap-2 text-primary">
                <Sparkles className="h-5 w-5" />
                <span className="text-xs font-semibold uppercase tracking-widest">
                  Copilot
                </span>
              </div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                Ask your plant anything.
              </h1>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                Search across procedures, SOPs, work orders, and incident
                reports. Every answer cites its sources.
              </p>
              <div className="mt-6 grid gap-2 sm:grid-cols-2">
                {[
                  "What's the lockout procedure for pump P204?",
                  "Which incidents involved compressor C101 last year?",
                  "Summarize maintenance intervals for chiller units.",
                  "What PPE is required for hot work in Area 4?",
                ].map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-lg border border-border bg-surface p-3 text-left text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {turns.map((t) => (
                <TurnCard key={t.id} turn={t} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="sticky bottom-16 border-t border-border bg-surface/95 p-3 backdrop-blur md:bottom-0 md:p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask();
          }}
          className="mx-auto flex max-w-3xl items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask();
              }
            }}
            placeholder="Ask about equipment, procedures, incidents…"
            rows={1}
            className="min-h-11 max-h-40 flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button
            type="submit"
            disabled={!input.trim() || mutation.isPending}
            className="inline-flex h-11 items-center justify-center gap-1.5 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}

function TurnCard({ turn }: { turn: Turn }) {
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary/15 px-4 py-2.5 text-sm text-foreground">
          {turn.question}
        </div>
      </div>

      <div className="rounded-2xl rounded-tl-sm border border-border bg-surface p-4">
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
          <MessageSquare className="h-3.5 w-3.5" /> Answer
        </div>

        {turn.loading ? (
          <TypingDots />
        ) : turn.error ? (
          <ErrorBanner error={turn.error} />
        ) : turn.response?.insufficient_evidence ? (
          <EmptyState
            title="Not enough evidence to answer"
            description="I couldn't find supporting content in the ingested documents. Try rephrasing, or ingest more source material."
          />
        ) : turn.response ? (
          <div className="space-y-4">
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {turn.response.answer}
            </p>
            {turn.response.citations?.length ? (
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Sources
                </p>
                <CitationList citations={turn.response.citations} />
              </div>
            ) : null}
            <ConfidenceBar value={turn.response.confidence} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 py-2">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="h-2 w-2 animate-bounce rounded-full bg-primary/70"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </div>
  );
}
