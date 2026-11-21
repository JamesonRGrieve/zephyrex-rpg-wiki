// SPDX-License-Identifier: AGPL-3.0-or-later
// The wiki's lite API, as an app composing the wiki mounts it (@zephyrex-rpg/wiki/lite); the app's own
// /v1/extension answers first.
import { wikiLite } from '@zephyrex-rpg/wiki/lite';
import { prisma } from '~/lib/prisma';

export const { GET, POST, PUT, DELETE } = wikiLite({ prisma });
