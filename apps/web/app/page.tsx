import { ArrowRight, BookOpen, MoonStar, Sparkles, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

import { ChatExperience } from '@/components/ChatExperience';
import { DailyWisdomCard } from '@/components/DailyWisdomCard';

const pillars = [
  {
    title: 'Ask Krishna Thoughts',
    description: 'Find a quiet moment to reflect on what matters and choose your next step with care.',
    icon: Sparkles,
  },
  {
    title: 'Daily Gita Wisdom',
    description: 'Read an original Sanskrit verse from the Bhagavad Gita, with its source.',
    icon: BookOpen,
  },
  {
    title: 'Safe Spiritual Guidance',
    description: 'Explore thoughtful guidance inspired by the Gita, shared as reflection—not divine authority.',
    icon: ShieldCheck,
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-sand text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-14 flex items-center justify-between rounded-full border border-slate-200/80 bg-white/70 px-4 py-3 backdrop-blur-md shadow-soft">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-night text-sm font-semibold text-white">
              KG
            </div>
            <div>
              <div className="text-base font-semibold tracking-wide">Krishna Guidance</div>
              <div className="text-xs text-slate-500">Wisdom with clarity, compassion, and safety</div>
            </div>
          </div>
          <nav className="hidden items-center gap-6 text-sm text-slate-600 md:flex">
            <a href="#features">Features</a>
            <a href="#chat">Chat</a>
            <a href="#safety">Safety</a>
          </nav>
          <Link href="#chat" className="rounded-full bg-night px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800">
            Get started
          </Link>
        </header>

        <section className="grid items-center gap-10 pb-12 pt-8 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-sm text-amber-800">
              <MoonStar className="h-4 w-4" />
              Calm, source-grounded spiritual guidance
            </div>
            <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
              A modern spiritual companion inspired by the wisdom of the Bhagavad Gita.
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">
              Thoughtful guidance for life decisions, emotional clarity, and deeper reflection—without pretending to be divine authority.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link href="#chat" className="inline-flex items-center gap-2 rounded-full bg-night px-5 py-3 text-sm font-medium text-white shadow-soft transition hover:bg-slate-800">
                Explore the platform <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="#safety" className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-700 transition hover:border-slate-400">
                Safety and ethics
              </Link>
            </div>
          </div>

          <DailyWisdomCard />
        </section>

        <section id="features" className="py-16">
          <div className="mb-10 text-center">
            <div className="text-sm font-medium uppercase tracking-[0.25em] text-slate-500">Experience</div>
            <h2 className="mt-3 text-3xl font-semibold text-slate-900">Built for clarity, reflection, and growth</h2>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {pillars.map(({ title, description, icon: Icon }) => (
              <div key={title} className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 inline-flex rounded-2xl bg-slate-100 p-3 text-slate-800">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="chat" className="py-16">
          <ChatExperience />
        </section>

        <section id="safety" className="py-16">
          <div className="rounded-[32px] border border-slate-200 bg-night p-8 text-slate-100 shadow-soft">
            <h2 className="text-3xl font-semibold">Safety and ethics by design</h2>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-700 bg-slate-900/50 p-5">
                <div className="text-lg font-semibold">Transparent AI</div>
                <p className="mt-2 text-sm leading-7 text-slate-300">Guidance is AI-generated and inspired by the Bhagavad Gita. It is not a divine message.</p>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-900/50 p-5">
                <div className="text-lg font-semibold">No false authority</div>
                <p className="mt-2 text-sm leading-7 text-slate-300">The experience avoids claiming divine power, manipulating dependence, or replacing professional care.</p>
              </div>
              <div className="rounded-2xl border border-slate-700 bg-slate-900/50 p-5">
                <div className="text-lg font-semibold">Evidence-grounded</div>
                <p className="mt-2 text-sm leading-7 text-slate-300">When a source verse is relevant, its original Sanskrit text and reference are shown separately.</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
