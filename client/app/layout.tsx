import type { Metadata } from 'next';
import { JetBrains_Mono, Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';
import { APP_NAME } from '@/components/brand';
import { Toaster } from '@/components/ui/sonner';

const sans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jakarta',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-jetbrains',
});

export const metadata: Metadata = {
  title: {
    default: `${APP_NAME} — get the exact line to change`,
    template: `%s · ${APP_NAME}`,
  },
  description:
    'Compare your code against a curated reference solution and get the exact file, line, and fix for your error.',
  applicationName: APP_NAME,
  generator: 'Rakib',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${sans.variable} ${mono.variable}`}>
      <body className="font-sans antialiased">
        {children}
        <Toaster theme="dark" />
      </body>
    </html>
  );
}
