-- AlterTable
ALTER TABLE "Campaign" ADD COLUMN "clockMinutes" INTEGER;

-- AlterTable
ALTER TABLE "Person" ADD COLUMN "motivations" TEXT;
ALTER TABLE "Person" ADD COLUMN "routine" TEXT;

-- CreateTable
CREATE TABLE "PersonMove" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "personId" TEXT NOT NULL,
    "campaignId" TEXT,
    "fromLocationId" TEXT,
    "toLocationId" TEXT NOT NULL,
    "atMinutes" INTEGER,
    "reason" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "PersonMove_personId_idx" ON "PersonMove"("personId");

