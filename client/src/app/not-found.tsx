// SPDX-License-Identifier: AGPL-3.0-or-later
import Link from 'next/link';
import type { ReactNode } from 'react';

/** An address that isn't a page: said plainly, in the app's own theme, with the way back. */
export default function NotFound(): ReactNode {
  return (
    <main className='mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-16'>
      <h1 className='text-3xl font-semibold tracking-tight'>Page not found</h1>
      <p className='text-muted-foreground'>There is nothing at this address. It may have moved, or the link may be wrong.</p>
      <p className='flex flex-wrap gap-4'>
        <Link href='/w' className='inline-flex min-h-11 items-center underline-offset-4 hover:underline'>
          Your worlds
        </Link>
        <Link href='/' className='inline-flex min-h-11 items-center underline-offset-4 hover:underline'>
          Home
        </Link>
      </p>
    </main>
  );
}
