-- CreateTable
CREATE TABLE "KnownFact" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "personId" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "text" TEXT,
    "learnedInJournalId" TEXT,
    "campaignId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "KnownFact_personId_idx" ON "KnownFact"("personId");

-- CreateIndex
CREATE INDEX "KnownFact_targetEntityId_idx" ON "KnownFact"("targetEntityId");

