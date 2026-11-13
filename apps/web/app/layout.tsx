import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Krishna Guidance',
  description: 'A peaceful, spiritually grounded AI guidance experience inspired by the Bhagavad Gita.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
