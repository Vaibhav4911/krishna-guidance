'use client';

import { FormEvent, useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { AuthResponse, logout, signIn, signUp } from '@/lib/api';

type AuthMode = 'signup' | 'login';

export function ChatExperience() {
  const [mode, setMode] = useState<AuthMode>('signup');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [session, setSession] = useState<AuthResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result =
        mode === 'signup'
          ? await signUp(email, password, name)
          : await signIn(email, password);
      setSession(result);
      setPassword('');
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : 'Unable to authenticate.');
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    if (!session) return;
    setBusy(true);
    setError('');
    try {
      await logout(session.access_token);
      setSession(null);
      setMode('login');
      setNotice('You have been signed out.');
    } catch (logoutError) {
      setError(logoutError instanceof Error ? logoutError.message : 'Unable to sign out.');
    } finally {
      setBusy(false);
    }
  }

  if (session) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4">
          <div className="text-sm text-slate-600">
            Signed in as <span className="font-medium text-slate-900">{session.user.email}</span>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={busy}
            className="rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
          >
            Sign out
          </button>
        </div>
        {error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null}
        <ChatPanel accessToken={session.access_token} />
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-xl rounded-[32px] border border-slate-200 bg-white p-6 shadow-soft sm:p-8">
      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Your private space</div>
      <h3 className="mt-2 text-2xl font-semibold text-slate-900">
        {mode === 'signup' ? 'Create your account' : 'Welcome back'}
      </h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        Sign in securely with your email and password. Your password is stored as a one-way hash.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {mode === 'signup' ? (
          <div>
            <label htmlFor="auth-name" className="mb-1 block text-sm font-medium text-slate-700">
              Name <span className="font-normal text-slate-500">(optional)</span>
            </label>
            <input
              id="auth-name"
              type="text"
              autoComplete="name"
              maxLength={255}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500"
            />
          </div>
        ) : null}

        <div>
          <label htmlFor="auth-email" className="mb-1 block text-sm font-medium text-slate-700">
            Email address
          </label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            maxLength={255}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500"
          />
        </div>

        <div>
          <label htmlFor="auth-password" className="mb-1 block text-sm font-medium text-slate-700">
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            minLength={mode === 'signup' ? 8 : 1}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500"
          />
          {mode === 'signup' ? (
            <p className="mt-1 text-xs text-slate-500">Use at least 8 characters.</p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-night px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {busy ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-slate-600">
        {mode === 'signup' ? 'Already have an account?' : 'New here?'}{' '}
        <button
          type="button"
          onClick={() => {
            setMode(mode === 'signup' ? 'login' : 'signup');
            setPassword('');
            setError('');
            setNotice('');
          }}
          className="font-medium text-slate-900 underline underline-offset-4"
        >
          {mode === 'signup' ? 'Sign in' : 'Create an account'}
        </button>
      </p>

      {notice ? <p role="status" className="mt-4 text-sm text-emerald-800">{notice}</p> : null}
      {error ? <p role="alert" className="mt-4 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
