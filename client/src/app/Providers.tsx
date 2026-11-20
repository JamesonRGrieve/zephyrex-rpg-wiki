'use client';
// SPDX-License-Identifier: AGPL-3.0-or-later
import type { ReactNode } from 'react';
import { ZephyrexApp } from 'zephyrex';
import config from '~/zephyrex.config';

/**
 * The framework shell, imported on the client: the config carries the extensions' page
 * components, which a server layout cannot pass to a client component as a prop.
 */
export function Providers({ children }: { children: ReactNode }): ReactNode {
  return <ZephyrexApp config={config}>{children}</ZephyrexApp>;
}
