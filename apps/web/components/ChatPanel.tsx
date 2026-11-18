'use client';

import { useEffect, useRef, useState } from 'react';
import {
  Citation,
  ConversationMessage,
  GuidanceLanguage,
  postChatMessage,
} from '@/lib/api';

type ChatTurn = ConversationMessage & { citations?: Citation[] };

function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      <h4 className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">
        Related Gita verses
      </h4>
      {citations.map((citation, index) => (
        <figure
          key={`${citation.chapter}-${citation.verse}-${index}`}
          className="rounded-xl border border-slate-200 bg-white p-4"
        >
          <figcaption className="text-xs font-medium text-slate-600">
            Bhagavad Gita, Chapter {citation.chapter}
            {citation.verse ? `, Verse ${citation.verse}` : ' · verse number not verified'}
            {' · '}
            {citation.translation}
          </figcaption>
          <blockquote className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">
            {citation.quote}
          </blockquote>
          {citation.meaning || citation.explanation ? (
            <div className="mt-4 space-y-3 border-t border-slate-100 pt-3">
              {citation.meaning ? (
                <div>
                  <div className="text-xs font-semibold text-slate-600">Simple meaning</div>
                  <p className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-700">
                    {citation.meaning}
                  </p>
                </div>
              ) : null}
              {citation.explanation ? (
                <div>
                  <div className="text-xs font-semibold text-slate-600">In detail</div>
                  <p className="mt-1 whitespace-pre-line text-sm leading-6 text-slate-700">
                    {citation.explanation}
                  </p>
                </div>
              ) : null}
            </div>
          ) : null}
          {citation.source_url ? (
            <a
              className="mt-2 inline-block text-xs text-slate-500 underline"
              href={citation.source_url}
              target="_blank"
              rel="noreferrer"
            >
              Source: {citation.source}
            </a>
          ) : null}
        </figure>
      ))}
    </div>
  );
}

export function ChatPanel({ accessToken }: { accessToken: string }) {
  const [message, setMessage] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [language, setLanguage] = useState<GuidanceLanguage>('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const conversationEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [turns, loading]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const submittedMessage = message.trim();
    if (!submittedMessage || loading) return;

    setLoading(true);
    setError('');

    try {
      const history: ConversationMessage[] = turns.slice(-8).map((turn) => {
        const citedVerses = (turn.citations ?? []).map(
          (citation) => {
            const reference = `Bhagavad Gita ${citation.chapter}:${citation.verse ?? '?'}`;
            return [reference, citation.meaning, citation.explanation]
              .filter(Boolean)
              .join(' ');
          },
        );
        const content = [turn.content, ...citedVerses].filter(Boolean).join('\n');
        const citationIds =
          turn.role === 'assistant'
            ? (turn.citations ?? [])
                .filter((citation) => citation.verse !== null)
                .map((citation) => `${citation.chapter}:${citation.verse}`)
            : [];
        return {
          role: turn.role,
          content: content.slice(0, 3000),
          citation_ids: citationIds,
        };
      });
      const response = await postChatMessage(
        submittedMessage,
        accessToken,
        language,
        history,
      );
      setTurns((current) => [
        ...current,
        { role: 'user', content: submittedMessage },
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          citation_ids: response.citations
            .filter((citation) => citation.verse !== null)
            .map((citation) => `${citation.chapter}:${citation.verse}`),
        },
      ]);
      setMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-soft">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Ask Krishna</div>
        <h3 className="mt-2 text-2xl font-semibold text-slate-900">Reflect with guidance</h3>
        <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-500">
          Simple English or Hindi guidance inspired by the Gita—not Lord Krishna. Verse meanings are simplified reflections, not authoritative translations. Your recent messages help with follow-up questions.
        </p>
      </div>

      {turns.length > 0 ? (
        <div aria-label="Conversation" aria-live="polite" className="mb-6 space-y-4">
          {turns.map((turn, index) =>
            turn.role === 'user' ? (
              <div key={`user-${index}`} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-night px-4 py-3 text-sm leading-6 text-white">
                  {turn.content}
                </div>
              </div>
            ) : (
              <article
                key={`assistant-${index}`}
                className="max-w-[95%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 p-4"
              >
                <div className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">
                  Gita-inspired response
                </div>
                <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-700">
                  {turn.content}
                </p>
                <CitationList citations={turn.citations ?? []} />
              </article>
            ),
          )}
          {loading ? (
            <div className="max-w-[95%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
              Reflecting...
            </div>
          ) : null}
          <div ref={conversationEndRef} />
        </div>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="mb-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
        >
          {error}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={4}
          maxLength={3000}
          aria-label="Your message"
          placeholder={
            turns.length > 0
              ? 'Ask a follow-up question...'
              : 'Share what feels heavy, confusing, or uncertain in your life...'
          }
          className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 outline-none transition focus:border-slate-400 focus:bg-white"
        />

        <div className="flex items-center justify-between gap-3">
          <div>
            <label htmlFor="guidance-language" className="mb-1 block text-xs text-slate-500">
              Response language
            </label>
            <select
              id="guidance-language"
              value={language}
              onChange={(event) => {
                const value = event.currentTarget.value;
                if (value === 'en' || value === 'hi') {
                  setLanguage(value);
                }
              }}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading || !message.trim()}
            className="rounded-full bg-night px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Reflecting...' : turns.length > 0 ? 'Send' : 'Seek guidance'}
          </button>
        </div>
      </form>
    </section>
  );
}
