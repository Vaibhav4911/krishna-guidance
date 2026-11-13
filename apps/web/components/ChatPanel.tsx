'use client';

import { useState } from 'react';
import { Citation, GuidanceLanguage, postChatMessage } from '@/lib/api';

export function ChatPanel({ accessToken }: { accessToken: string }) {
  const [message, setMessage] = useState('');
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [language, setLanguage] = useState<GuidanceLanguage>('en');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await postChatMessage(message, accessToken, language);
      setAnswer(response.answer);
      setCitations(response.citations);
      setMessage('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-soft">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Ask Krishna</div>
          <h3 className="mt-2 text-2xl font-semibold text-slate-900">Reflect with guidance</h3>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-500">
            AI-generated, Krishna-inspired guidance—not Lord Krishna. Your message and retrieved Sanskrit verses are sent to OpenAI.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          rows={5}
          maxLength={3000}
          aria-label="Your question"
          placeholder="Share what feels heavy, confusing, or uncertain in your life..."
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
                if (value === 'en' || value === 'hi' || value === 'sa') {
                  setLanguage(value);
                }
              }}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="sa">Sanskrit</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-night px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? 'Reflecting...' : 'Seek guidance'}
          </button>
        </div>
      </form>

      {error ? <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

      {answer ? (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Response</div>
          <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">{answer}</p>
          {citations.length > 0 ? (
            <div className="mt-5 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">
                Retrieved passages
              </h4>
              {citations.map((citation, index) => (
                <figure key={`${citation.chapter}-${index}`} className="rounded-xl border border-slate-200 bg-white p-4">
                  <figcaption className="text-xs font-medium text-slate-600">
                    Bhagavad Gita, Chapter {citation.chapter}
                    {citation.verse ? `, Verse ${citation.verse}` : ' · verse number not verified'}
                    {' · '}
                    {citation.translation}
                  </figcaption>
                  <blockquote className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">
                    {citation.quote}
                  </blockquote>
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
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
