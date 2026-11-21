-- AlterTable
ALTER TABLE "Location" ADD COLUMN "isTemplate" BOOLEAN;

-- AlterTable
ALTER TABLE "Person" ADD COLUMN "isTemplate" BOOLEAN;

-- AlterTable
ALTER TABLE "Faction" ADD COLUMN "isTemplate" BOOLEAN;

-- AlterTable
ALTER TABLE "Item" ADD COLUMN "isTemplate" BOOLEAN;

-- AlterTable
ALTER TABLE "Journal" ADD COLUMN "isTemplate" BOOLEAN;

-- AlterTable
ALTER TABLE "Hook" ADD COLUMN "isTemplate" BOOLEAN;

-- CreateTable
CREATE TABLE "RecordMetadata" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT,
    "valueType" TEXT,
    "ordinal" INTEGER NOT NULL DEFAULT 0,
    "isPrivate" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "PropertyKit" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "properties" TEXT NOT NULL DEFAULT '[]',
    "campaignId" TEXT,
    "settingId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);

-- CreateIndex
CREATE INDEX "RecordMetadata_targetEntityId_idx" ON "RecordMetadata"("targetEntityId");

-- CreateIndex
CREATE UNIQUE INDEX "RecordMetadata_targetEntityType_targetEntityId_key_key" ON "RecordMetadata"("targetEntityType", "targetEntityId", "key");

-- CreateIndex
CREATE INDEX "PropertyKit_createdById_idx" ON "PropertyKit"("createdById");

