// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/plot: a world's plot board. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { PlotPage } from '@zephyrex-rpg/wiki/pages/PlotPage';

export default function Page(): ReactElement {
  const params = useParams<{ world: string }>();
  return <PlotPage {...params} />;
}
