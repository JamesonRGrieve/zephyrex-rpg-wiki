// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/** /w/[world]/taxonomy: a world's tags and statuses. The page is the wiki package's (S7), as an app composing the wiki shows it. */
import { useParams } from 'next/navigation';
import type { ReactElement } from 'react';
import { TaxonomyPage } from '@zephyrex-rpg/wiki/pages/TaxonomyPage';

export default function Page(): ReactElement {
  const params = useParams<{ world: string }>();
  return <TaxonomyPage {...params} />;
}
