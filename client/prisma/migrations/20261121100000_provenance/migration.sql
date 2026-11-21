-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Campaign" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "settingId" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);
INSERT INTO "new_Campaign" ("createdAt", "createdById", "description", "id", "name", "settingId", "updatedAt", "updatedById") SELECT "createdAt", "createdById", "description", "id", "name", "settingId", "updatedAt", "updatedById" FROM "Campaign";
DROP TABLE "Campaign";
ALTER TABLE "new_Campaign" RENAME TO "Campaign";
CREATE INDEX "Campaign_createdById_idx" ON "Campaign"("createdById");
CREATE TABLE "new_Location" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "parentId" TEXT,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "associatedPersonId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Location" ("aliases", "associatedPersonId", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "parentId", "settingId", "updatedAt", "updatedById") SELECT "aliases", "associatedPersonId", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "parentId", "settingId", "updatedAt", "updatedById" FROM "Location";
DROP TABLE "Location";
ALTER TABLE "new_Location" RENAME TO "Location";
CREATE INDEX "Location_createdById_idx" ON "Location"("createdById");
CREATE INDEX "Location_deletedAt_idx" ON "Location"("deletedAt");
CREATE INDEX "Location_campaignId_idx" ON "Location"("campaignId");
CREATE INDEX "Location_parentId_idx" ON "Location"("parentId");
CREATE INDEX "Location_associatedPersonId_idx" ON "Location"("associatedPersonId");
CREATE INDEX "Location_settingId_idx" ON "Location"("settingId");
CREATE TABLE "new_Person" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "voice" TEXT,
    "locationId" TEXT,
    "gender" TEXT,
    "birthDate" DATETIME,
    "deathDate" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Person" ("aliases", "birthDate", "campaignId", "canonLevel", "createdAt", "createdById", "deathDate", "deletedAt", "description", "entry", "gender", "id", "isTemplate", "keywords", "kind", "locationId", "lore", "name", "settingId", "updatedAt", "updatedById", "voice") SELECT "aliases", "birthDate", "campaignId", "canonLevel", "createdAt", "createdById", "deathDate", "deletedAt", "description", "entry", "gender", "id", "isTemplate", "keywords", "kind", "locationId", "lore", "name", "settingId", "updatedAt", "updatedById", "voice" FROM "Person";
DROP TABLE "Person";
ALTER TABLE "new_Person" RENAME TO "Person";
CREATE INDEX "Person_createdById_idx" ON "Person"("createdById");
CREATE INDEX "Person_deletedAt_idx" ON "Person"("deletedAt");
CREATE INDEX "Person_campaignId_idx" ON "Person"("campaignId");
CREATE INDEX "Person_settingId_idx" ON "Person"("settingId");
CREATE TABLE "new_Faction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "parentId" TEXT,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Faction" ("aliases", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "parentId", "settingId", "updatedAt", "updatedById") SELECT "aliases", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "parentId", "settingId", "updatedAt", "updatedById" FROM "Faction";
DROP TABLE "Faction";
ALTER TABLE "new_Faction" RENAME TO "Faction";
CREATE INDEX "Faction_createdById_idx" ON "Faction"("createdById");
CREATE INDEX "Faction_deletedAt_idx" ON "Faction"("deletedAt");
CREATE INDEX "Faction_campaignId_idx" ON "Faction"("campaignId");
CREATE INDEX "Faction_parentId_idx" ON "Faction"("parentId");
CREATE INDEX "Faction_settingId_idx" ON "Faction"("settingId");
CREATE TABLE "new_Item" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "weight" REAL,
    "baseValue" REAL,
    "stackSize" INTEGER NOT NULL DEFAULT 1,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Item" ("aliases", "baseValue", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "settingId", "stackSize", "updatedAt", "updatedById", "weight") SELECT "aliases", "baseValue", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "lore", "name", "settingId", "stackSize", "updatedAt", "updatedById", "weight" FROM "Item";
DROP TABLE "Item";
ALTER TABLE "new_Item" RENAME TO "Item";
CREATE INDEX "Item_createdById_idx" ON "Item"("createdById");
CREATE INDEX "Item_deletedAt_idx" ON "Item"("deletedAt");
CREATE INDEX "Item_campaignId_idx" ON "Item"("campaignId");
CREATE INDEX "Item_settingId_idx" ON "Item"("settingId");
CREATE TABLE "new_Journal" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "locationId" TEXT,
    "authorPersonId" TEXT,
    "sessionNumber" INTEGER,
    "occurredAt" DATETIME,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Journal" ("aliases", "authorPersonId", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "locationId", "lore", "name", "occurredAt", "sessionNumber", "settingId", "updatedAt", "updatedById") SELECT "aliases", "authorPersonId", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "id", "isTemplate", "keywords", "kind", "locationId", "lore", "name", "occurredAt", "sessionNumber", "settingId", "updatedAt", "updatedById" FROM "Journal";
DROP TABLE "Journal";
ALTER TABLE "new_Journal" RENAME TO "Journal";
CREATE INDEX "Journal_createdById_idx" ON "Journal"("createdById");
CREATE INDEX "Journal_campaignId_idx" ON "Journal"("campaignId");
CREATE INDEX "Journal_deletedAt_idx" ON "Journal"("deletedAt");
CREATE INDEX "Journal_settingId_idx" ON "Journal"("settingId");
CREATE TABLE "new_Hook" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "giverPersonId" TEXT,
    "giverFactionId" TEXT,
    "requires" TEXT,
    "excuse" TEXT,
    "resolvedAt" DATETIME,
    "resolvedJournalId" TEXT,
    "campaignId" TEXT,
    "settingId" TEXT,
    "canonLevel" TEXT,
    "isTemplate" BOOLEAN,
    "aliases" TEXT,
    "keywords" TEXT,
    "lore" TEXT,
    "provenance" TEXT NOT NULL DEFAULT 'homebrew',
    "source" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);
INSERT INTO "new_Hook" ("aliases", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "excuse", "giverFactionId", "giverPersonId", "id", "isTemplate", "keywords", "kind", "lore", "name", "requires", "resolvedAt", "resolvedJournalId", "settingId", "updatedAt", "updatedById") SELECT "aliases", "campaignId", "canonLevel", "createdAt", "createdById", "deletedAt", "description", "entry", "excuse", "giverFactionId", "giverPersonId", "id", "isTemplate", "keywords", "kind", "lore", "name", "requires", "resolvedAt", "resolvedJournalId", "settingId", "updatedAt", "updatedById" FROM "Hook";
DROP TABLE "Hook";
ALTER TABLE "new_Hook" RENAME TO "Hook";
CREATE INDEX "Hook_createdById_idx" ON "Hook"("createdById");
CREATE INDEX "Hook_campaignId_idx" ON "Hook"("campaignId");
CREATE INDEX "Hook_deletedAt_idx" ON "Hook"("deletedAt");
CREATE INDEX "Hook_settingId_idx" ON "Hook"("settingId");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

