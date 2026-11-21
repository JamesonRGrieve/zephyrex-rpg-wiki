// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w: the person's worlds. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import type { ReactElement } from 'react';
import { WorldsPage } from '@zephyrex-rpg/wiki/pages/WorldsPage';

export default function Page(): ReactElement {
  return <WorldsPage />;
}
