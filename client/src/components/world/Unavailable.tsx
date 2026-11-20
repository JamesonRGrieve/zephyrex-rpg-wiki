// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ReactElement } from 'react';

/** Said when this deployment's back end doesn't serve what the page shows (its /v1/extension). */
export function Unavailable({ what }: { what: string }): ReactElement {
  return <p className='rounded-xl border border-dashed p-8 text-center text-muted-foreground'>{`This server doesn’t keep ${what}.`}</p>;
}
