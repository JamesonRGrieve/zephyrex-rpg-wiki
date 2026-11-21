// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/[kind]/[id]: one record's page. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { RecordPage } from '@zephyrex-rpg/wiki/pages/RecordPage';

export default function Page(): ReactElement {
  const params = useParams<{ world: string; kind: string; id: string }>();
  return <RecordPage {...params} />;
}
