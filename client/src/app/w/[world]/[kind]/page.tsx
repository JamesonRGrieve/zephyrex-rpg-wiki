// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/[kind]: one world's records of a kind. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { KindPage } from '@zephyrex-rpg/wiki/pages/KindPage';

export default function Page(): ReactElement {
  const params = useParams<{ world: string; kind: string }>();
  return <KindPage {...params} />;
}
