-- AlterTable
ALTER TABLE "Location" ADD COLUMN "deletedAt" DATETIME;

-- AlterTable
ALTER TABLE "Person" ADD COLUMN "deletedAt" DATETIME;

-- AlterTable
ALTER TABLE "Faction" ADD COLUMN "deletedAt" DATETIME;

-- AlterTable
ALTER TABLE "Item" ADD COLUMN "deletedAt" DATETIME;

-- CreateIndex
CREATE INDEX "Location_deletedAt_idx" ON "Location"("deletedAt");

-- CreateIndex
CREATE INDEX "Person_deletedAt_idx" ON "Person"("deletedAt");

-- CreateIndex
CREATE INDEX "Faction_deletedAt_idx" ON "Faction"("deletedAt");

-- CreateIndex
CREATE INDEX "Item_deletedAt_idx" ON "Item"("deletedAt");

