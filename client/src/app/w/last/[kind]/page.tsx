// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/last/[kind]: the sidebar's Places, People… opening the setting or campaign last shown. The page is the wiki package's (S7). */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { LastScopePage } from '@zephyrex-rpg/wiki/pages/LastScopePage';

export default function Page(): ReactElement {
  const params = useParams<{ kind: string }>();
  return <LastScopePage {...params} />;
}
