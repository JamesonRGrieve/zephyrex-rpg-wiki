-- AlterTable
ALTER TABLE "Campaign" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Location" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Location" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Person" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Person" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Faction" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Faction" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Item" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Item" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Journal" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Journal" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Hook" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Hook" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Taxon" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Taxon" ADD COLUMN "settingId" TEXT;

-- AlterTable
ALTER TABLE "Status" ADD COLUMN "canonLevel" TEXT;
ALTER TABLE "Status" ADD COLUMN "settingId" TEXT;

-- CreateTable
CREATE TABLE "Setting" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Setting_createdById_idx" ON "Setting"("createdById");

-- CreateIndex
CREATE INDEX "Location_settingId_idx" ON "Location"("settingId");

-- CreateIndex
CREATE INDEX "Person_settingId_idx" ON "Person"("settingId");

-- CreateIndex
CREATE INDEX "Faction_settingId_idx" ON "Faction"("settingId");

-- CreateIndex
CREATE INDEX "Item_settingId_idx" ON "Item"("settingId");

-- CreateIndex
CREATE INDEX "Journal_settingId_idx" ON "Journal"("settingId");

-- CreateIndex
CREATE INDEX "Hook_settingId_idx" ON "Hook"("settingId");

-- CreateIndex
CREATE INDEX "Taxon_settingId_idx" ON "Taxon"("settingId");

-- CreateIndex
CREATE INDEX "Status_settingId_idx" ON "Status"("settingId");

