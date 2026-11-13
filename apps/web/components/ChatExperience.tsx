'use client';

import { FormEvent, useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { AuthResponse, logout, requestEmailOtp, verifyEmailOtp } from '@/lib/api';

export function ChatExperience() {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [otpRequested, setOtpRequested] = useState(false);
  const [session, setSession] = useState<AuthResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function handleRequestOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await requestEmailOtp(email);
      setOtpRequested(true);
      setNotice('If this address can receive sign-in mail, a code has been sent.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to request a code.');
    } finally {
      setBusy(false);
    }
  }

  async function handleVerifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await verifyEmailOtp(email, otp);
      setSession(result);
      setOtp('');
      setNotice('');
    } catch (verifyError) {
      setError(verifyError instanceof Error ? verifyError.message : 'Unable to verify the code.');
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
      setOtpRequested(false);
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
      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Private sign-in</div>
      <h3 className="mt-2 text-2xl font-semibold text-slate-900">Continue with email</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        We’ll email a one-time sign-in code. Your access token stays in memory in this tab and is not saved to browser storage.
      </p>

      <form onSubmit={handleRequestOtp} className="mt-6 space-y-3">
        <label htmlFor="auth-email" className="block text-sm font-medium text-slate-700">Email address</label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            maxLength={255}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-500"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-full bg-night px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
          >
            {busy ? 'Sending...' : 'Send code'}
          </button>
        </div>
      </form>

      {otpRequested ? (
        <form onSubmit={handleVerifyOtp} className="mt-5 space-y-3">
          <label htmlFor="auth-otp" className="block text-sm font-medium text-slate-700">Six-digit code</label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              id="auth-otp"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              minLength={6}
              maxLength={6}
              required
              value={otp}
              onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))}
              className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm tracking-[0.3em] outline-none focus:border-slate-500"
            />
            <button
              type="submit"
              disabled={busy || otp.length !== 6}
              className="rounded-full bg-night px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
            >
              {busy ? 'Verifying...' : 'Verify code'}
            </button>
          </div>
        </form>
      ) : null}

      {notice ? <p role="status" className="mt-4 text-sm text-emerald-800">{notice}</p> : null}
      {error ? <p role="alert" className="mt-4 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
