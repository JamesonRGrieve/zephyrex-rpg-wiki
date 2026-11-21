// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/about: a world itself, and where it came from. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { WorldPage } from '@zephyrex-rpg/wiki/pages/WorldPage';

export default function Page(): ReactElement {
  const params = useParams<{ world: string }>();
  return <WorldPage {...params} />;
}
