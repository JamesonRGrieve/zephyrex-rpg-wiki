-- CreateTable
CREATE TABLE "Taxon" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "parentId" TEXT,
    "kind" TEXT,
    "colour" TEXT,
    "campaignId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);

-- CreateTable
CREATE TABLE "EntityTaxon" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "taxonId" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "Status" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "kind" TEXT,
    "colour" TEXT,
    "campaignId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);

-- CreateTable
CREATE TABLE "EntityStatus" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "statusId" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "Relationship" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "personId" TEXT,
    "factionId" TEXT,
    "targetPersonId" TEXT,
    "targetFactionId" TEXT,
    "kind" TEXT,
    "discriminator" TEXT,
    "intensity" REAL,
    "qualifier" TEXT,
    "validFrom" DATETIME,
    "validTo" DATETIME,
    "notes" TEXT,
    "colour" TEXT,
    "mirrorRelationshipId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Taxon_createdById_idx" ON "Taxon"("createdById");

-- CreateIndex
CREATE INDEX "Taxon_campaignId_idx" ON "Taxon"("campaignId");

-- CreateIndex
CREATE INDEX "Taxon_deletedAt_idx" ON "Taxon"("deletedAt");

-- CreateIndex
CREATE INDEX "EntityTaxon_targetEntityId_idx" ON "EntityTaxon"("targetEntityId");

-- CreateIndex
CREATE UNIQUE INDEX "EntityTaxon_taxonId_targetEntityType_targetEntityId_key" ON "EntityTaxon"("taxonId", "targetEntityType", "targetEntityId");

-- CreateIndex
CREATE INDEX "Status_createdById_idx" ON "Status"("createdById");

-- CreateIndex
CREATE INDEX "Status_deletedAt_idx" ON "Status"("deletedAt");

-- CreateIndex
CREATE UNIQUE INDEX "EntityStatus_targetEntityType_targetEntityId_key" ON "EntityStatus"("targetEntityType", "targetEntityId");

-- CreateIndex
CREATE INDEX "Relationship_createdById_idx" ON "Relationship"("createdById");

-- CreateIndex
CREATE INDEX "Relationship_personId_idx" ON "Relationship"("personId");

-- CreateIndex
CREATE INDEX "Relationship_factionId_idx" ON "Relationship"("factionId");

-- CreateIndex
CREATE INDEX "Relationship_targetPersonId_idx" ON "Relationship"("targetPersonId");

-- CreateIndex
CREATE INDEX "Relationship_targetFactionId_idx" ON "Relationship"("targetFactionId");

