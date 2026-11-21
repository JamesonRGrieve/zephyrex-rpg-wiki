-- CreateTable
CREATE TABLE "Journal" (
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
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);

-- CreateTable
CREATE TABLE "EntityPost" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "position" TEXT NOT NULL DEFAULT 'default',
    "ordinal" INTEGER NOT NULL DEFAULT 0,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Journal_createdById_idx" ON "Journal"("createdById");

-- CreateIndex
CREATE INDEX "Journal_campaignId_idx" ON "Journal"("campaignId");

-- CreateIndex
CREATE INDEX "Journal_deletedAt_idx" ON "Journal"("deletedAt");

-- CreateIndex
CREATE INDEX "EntityPost_createdById_idx" ON "EntityPost"("createdById");

-- CreateIndex
CREATE INDEX "EntityPost_targetEntityId_idx" ON "EntityPost"("targetEntityId");

