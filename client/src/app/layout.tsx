// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ReactNode } from 'react';
import { Providers } from './Providers';
import './globals.css';

export { metadata, viewport } from './metadata';

export default function RootLayout({ children }: { children: ReactNode }): ReactNode {
  return (
    <html lang='en' className='dark' suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
