-- AlterTable
ALTER TABLE "Hook" ADD COLUMN "excuse" TEXT;
ALTER TABLE "Hook" ADD COLUMN "requires" TEXT;
ALTER TABLE "Hook" ADD COLUMN "resolvedAt" DATETIME;
ALTER TABLE "Hook" ADD COLUMN "resolvedJournalId" TEXT;

-- CreateTable
CREATE TABLE "Disposition" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "personId" TEXT NOT NULL,
    "targetKind" TEXT NOT NULL,
    "targetPersonId" TEXT,
    "targetFactionId" TEXT,
    "attitude" TEXT NOT NULL,
    "isDefault" BOOLEAN NOT NULL DEFAULT false,
    "triggerHookId" TEXT,
    "note" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "RelationInfluence" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "relationshipId" TEXT NOT NULL,
    "hookId" TEXT NOT NULL,
    "toIntensity" REAL NOT NULL,
    "note" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Disposition_personId_idx" ON "Disposition"("personId");

-- CreateIndex
CREATE INDEX "Disposition_triggerHookId_idx" ON "Disposition"("triggerHookId");

-- CreateIndex
CREATE INDEX "RelationInfluence_relationshipId_idx" ON "RelationInfluence"("relationshipId");

-- CreateIndex
CREATE INDEX "RelationInfluence_hookId_idx" ON "RelationInfluence"("hookId");

