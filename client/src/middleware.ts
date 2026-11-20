// SPDX-License-Identifier: AGPL-3.0-or-later
import { createMiddleware } from 'zephyrex';
import appConfig from './zephyrex.config';

// The framework's auth middleware (session check against the configured API, private routes)
// plus any extension-provided middleware, built from this app's config.
export default createMiddleware(appConfig);
