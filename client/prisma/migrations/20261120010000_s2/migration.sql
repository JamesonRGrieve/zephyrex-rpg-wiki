-- AlterTable
ALTER TABLE "Location" ADD COLUMN "associatedPersonId" TEXT;

-- CreateTable
CREATE TABLE "Faction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "parentId" TEXT,
    "campaignId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "Item" (
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
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "ItemInstance" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "itemId" TEXT,
    "locationId" TEXT,
    "ownerPersonId" TEXT,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    "durability" REAL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "EntityInventory" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "targetEntityType" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "itemInstanceId" TEXT,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Faction_createdById_idx" ON "Faction"("createdById");

-- CreateIndex
CREATE INDEX "Faction_campaignId_idx" ON "Faction"("campaignId");

-- CreateIndex
CREATE INDEX "Faction_parentId_idx" ON "Faction"("parentId");

-- CreateIndex
CREATE INDEX "Item_createdById_idx" ON "Item"("createdById");

-- CreateIndex
CREATE INDEX "Item_campaignId_idx" ON "Item"("campaignId");

-- CreateIndex
CREATE INDEX "ItemInstance_createdById_idx" ON "ItemInstance"("createdById");

-- CreateIndex
CREATE INDEX "ItemInstance_itemId_idx" ON "ItemInstance"("itemId");

-- CreateIndex
CREATE INDEX "EntityInventory_createdById_idx" ON "EntityInventory"("createdById");

-- CreateIndex
CREATE INDEX "EntityInventory_targetEntityId_idx" ON "EntityInventory"("targetEntityId");

-- CreateIndex
CREATE INDEX "Location_associatedPersonId_idx" ON "Location"("associatedPersonId");

