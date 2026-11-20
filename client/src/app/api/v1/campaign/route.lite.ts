// SPDX-License-Identifier: AGPL-3.0-or-later
import { collectionRoutes, localOwner } from '@zephyrex/lite';
import { campaigns } from '~/lib/worldRecords';

// GET /v1/campaign (list) and POST /v1/campaign (create), as server-framework answers them.
export const { GET, POST } = collectionRoutes(campaigns, localOwner);
