-- CreateTable
CREATE TABLE "Hook" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL DEFAULT '',
    "entry" TEXT,
    "kind" TEXT,
    "giverPersonId" TEXT,
    "giverFactionId" TEXT,
    "campaignId" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT,
    "deletedAt" DATETIME
);

-- CreateTable
CREATE TABLE "HookDependency" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "parentHookId" TEXT NOT NULL,
    "childHookId" TEXT NOT NULL,
    "reason" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "PersonHook" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "personId" TEXT NOT NULL,
    "hookId" TEXT NOT NULL,
    "status" TEXT,
    "acceptedAt" DATETIME,
    "completedAt" DATETIME,
    "progress" REAL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateTable
CREATE TABLE "FactionHook" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "createdById" TEXT NOT NULL,
    "factionId" TEXT NOT NULL,
    "hookId" TEXT NOT NULL,
    "status" TEXT,
    "acceptedAt" DATETIME,
    "completedAt" DATETIME,
    "progress" REAL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    "updatedById" TEXT
);

-- CreateIndex
CREATE INDEX "Hook_createdById_idx" ON "Hook"("createdById");

-- CreateIndex
CREATE INDEX "Hook_campaignId_idx" ON "Hook"("campaignId");

-- CreateIndex
CREATE INDEX "Hook_deletedAt_idx" ON "Hook"("deletedAt");

-- CreateIndex
CREATE INDEX "HookDependency_childHookId_idx" ON "HookDependency"("childHookId");

-- CreateIndex
CREATE UNIQUE INDEX "HookDependency_parentHookId_childHookId_key" ON "HookDependency"("parentHookId", "childHookId");

-- CreateIndex
CREATE INDEX "PersonHook_hookId_idx" ON "PersonHook"("hookId");

-- CreateIndex
CREATE UNIQUE INDEX "PersonHook_personId_hookId_key" ON "PersonHook"("personId", "hookId");

-- CreateIndex
CREATE INDEX "FactionHook_hookId_idx" ON "FactionHook"("hookId");

-- CreateIndex
CREATE UNIQUE INDEX "FactionHook_factionId_hookId_key" ON "FactionHook"("factionId", "hookId");

