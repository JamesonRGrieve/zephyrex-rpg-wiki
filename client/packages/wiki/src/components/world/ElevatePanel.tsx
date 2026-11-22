// SPDX-License-Identifier: AGPL-3.0-or-later
'use client';
/**
 * A playthrough's person and its scenario (operator, 2026-11-22: NPCs authored mid-play are
 * campaign-only, "with an 'elevate to scenario' on their profile"): elevating copies them into the
 * scenario so later playthroughs have them; once there, the page links to the scenario's copy.
 */
import { ArrowUpFromLine } from 'lucide-react';
import Link from 'next/link';
import { type ReactElement, useState } from 'react';
import { Button } from 'zephyrex/ui/button';
import { WriteProblem } from './WriteProblem';

export function ElevatePanel({
  scenario,
  elevated,
  onElevate,
}: {
  /** The scenario this campaign is a playthrough of. */
  scenario: { name: string };
  /** The person's copy in the scenario, once elevated. */
  elevated: { name: string; href: string } | null;
  /** Elevates them; resolves to why it failed, or null. */
  onElevate: () => Promise<string | null>;
}): ReactElement {
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  return (
    <section aria-label='In the scenario' className='grid gap-2 rounded-xl border p-4'>
      {elevated !== null ? (
        <p className='text-sm'>
          In the scenario {scenario.name} as{' '}
          <Link href={elevated.href} className='underline-offset-4 hover:underline'>
            {elevated.name}
          </Link>
          : later playthroughs have them.
        </p>
      ) : (
        <>
          <p className='text-sm text-muted-foreground'>Made in this playthrough only. Elevate them to {scenario.name} so later playthroughs have them too.</p>
          <div>
            <Button
              type='button'
              className='h-11'
              disabled={busy}
              onClick={() => {
                setBusy(true);
                void onElevate().then((why) => {
                  setProblem(why);
                  setBusy(false);
                });
              }}
            >
              <ArrowUpFromLine aria-hidden />
              Elevate to scenario
            </Button>
          </div>
        </>
      )}
      <WriteProblem problem={problem} />
    </section>
  );
}
