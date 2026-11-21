// SPDX-License-Identifier: AGPL-3.0-or-later
import { cookies } from 'next/headers';
import type { ReactNode } from 'react';
import appConfig from '~/zephyrex.config';
import { Providers } from './Providers';
import './globals.css';

export { metadata, viewport } from './metadata';

/**
 * Reads the theme cookie, so the page renders in the person's theme from the first paint, and so
 * every page renders per request: the framework's CSP gives each response a script nonce, which a
 * prerendered page can't carry (the visual audit found /w's scripts all blocked when it was static).
 */
export default async function RootLayout({ children }: { children: ReactNode }): Promise<ReactNode> {
  const cookieStore = await cookies();
  const theme = cookieStore.get('theme')?.value ?? appConfig.app.defaultTheme ?? 'dark';
  const appearance = cookieStore.get('appearance')?.value ?? '';
  const htmlThemeClass = theme === 'dark' || theme === 'colorblind' || theme === 'colorblind-dark' ? theme : '';

  return (
    <html lang='en' className={htmlThemeClass} suppressHydrationWarning>
      <body className={[theme, appearance].filter(Boolean).join(' ')}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
