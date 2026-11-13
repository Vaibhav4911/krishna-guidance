export type Citation = {
  chapter: number;
  verse: number | null;
  source: string;
  source_url: string | null;
  language: string;
  translation: string;
  quote: string;
};

export type ChatMessageResponse = {
  answer: string;
  language: string;
  citations: Citation[];
  safety_mode: string;
};

export type DailyWisdomResponse = {
  passage: Citation;
  reflection: string;
};

export type GuidanceLanguage = 'en' | 'hi' | 'sa';

export type AuthResponse = {
  user: {
    id: number;
    email: string;
    name: string | null;
  };
  access_token: string;
  token_type: 'bearer';
  expires_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const message = typeof body?.detail === 'string' ? body.detail : fallback;
  return new Error(message);
}

export async function requestEmailOtp(email: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/otp/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!response.ok) throw await apiError(response, 'Unable to send a sign-in code.');
}

export async function verifyEmailOtp(email: string, otp: string): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/otp/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
  });
  if (!response.ok) throw await apiError(response, 'Unable to verify the sign-in code.');
  return (await response.json()) as AuthResponse;
}

export async function logout(accessToken: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw await apiError(response, 'Unable to end this session.');
}

export async function postChatMessage(
  message: string,
  accessToken: string,
  language: GuidanceLanguage = 'en',
): Promise<ChatMessageResponse> {
  const response = await fetch(`${API_URL}/api/v1/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ message, language }),
  });

  if (!response.ok) throw await apiError(response, 'Unable to fetch a guidance response.');
  return (await response.json()) as ChatMessageResponse;
}

export async function getDailyWisdom(): Promise<DailyWisdomResponse> {
  const response = await fetch(`${API_URL}/api/v1/daily-wisdom`);
  if (!response.ok) throw await apiError(response, 'Unable to fetch today’s passage.');
  return (await response.json()) as DailyWisdomResponse;
}
