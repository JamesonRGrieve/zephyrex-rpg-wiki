// SPDX-License-Identifier: AGPL-3.0-or-later
// jsdom stand-ins (matchMedia, ResizeObserver, pointer capture) and the toast reset come from
// zephyrex/testing/setup, listed first in vitest.config.ts; only this app's own needs are here.
import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  })),
  usePathname: vi.fn(() => '/'),
  useSearchParams: vi.fn(() => new URLSearchParams()),
  redirect: vi.fn(),
}));
