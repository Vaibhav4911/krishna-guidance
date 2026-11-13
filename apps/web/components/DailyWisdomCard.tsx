'use client';

import { useEffect, useState } from 'react';
import { Heart } from 'lucide-react';

import { DailyWisdomResponse, getDailyWisdom } from '@/lib/api';

export function DailyWisdomCard() {
  const [dailyWisdom, setDailyWisdom] = useState<DailyWisdomResponse | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getDailyWisdom()
      .then((response) => {
        if (active) setDailyWisdom(response);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load today’s passage.',
          );
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="rounded-[32px] border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <div className="text-sm uppercase tracking-[0.2em] text-slate-400">Today</div>
          <div className="mt-1 text-2xl font-semibold text-slate-900">Bhagavad Gita</div>
        </div>
        <div className="rounded-full bg-amber-100 p-2 text-amber-700">
          <Heart className="h-5 w-5" />
        </div>
      </div>
      {error ? (
        <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </p>
      ) : dailyWisdom ? (
        <div className="mt-6 space-y-4">
          <figure className="rounded-2xl bg-slate-50 p-4">
            <figcaption className="text-xs font-medium uppercase tracking-[0.15em] text-slate-500">
              Bhagavad Gita {dailyWisdom.passage.chapter}
              {dailyWisdom.passage.verse ? `:${dailyWisdom.passage.verse}` : ''}
            </figcaption>
            <blockquote className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">
              {dailyWisdom.passage.quote}
            </blockquote>
            <div className="mt-3 text-xs text-slate-500">
              {dailyWisdom.passage.translation}
            </div>
            {dailyWisdom.passage.source_url ? (
              <a
                className="mt-2 inline-block text-xs text-slate-500 underline"
                href={dailyWisdom.passage.source_url}
                target="_blank"
                rel="noreferrer"
              >
                Source: {dailyWisdom.passage.source}
              </a>
            ) : null}
          </figure>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Reflection</div>
            <p className="mt-3 text-sm leading-7 text-slate-600">{dailyWisdom.reflection}</p>
          </div>
        </div>
      ) : (
        <p role="status" className="mt-6 rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">
          Loading today’s source passage…
        </p>
      )}
    </div>
  );
}
