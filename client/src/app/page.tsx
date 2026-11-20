// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ReactNode } from 'react';
import { Landing } from '~/components/landing/Landing';

/**
 * The landing page, in both editions. The wiki has no screen to start on yet, so it never
 * redirects: its way in is the plan. When the first screen ships, lite goes straight to it and the
 * hosted build sends a signed-in person there (as zephyrex-rpg-ai's page does).
 */
export default function Home(): ReactNode {
  return <Landing />;
}
