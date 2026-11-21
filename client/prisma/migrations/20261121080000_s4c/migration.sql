-- AlterTable
ALTER TABLE "Location" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Location" ADD COLUMN "keywords" TEXT;

-- AlterTable
ALTER TABLE "Person" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Person" ADD COLUMN "keywords" TEXT;
ALTER TABLE "Person" ADD COLUMN "voice" TEXT;

-- AlterTable
ALTER TABLE "Faction" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Faction" ADD COLUMN "keywords" TEXT;

-- AlterTable
ALTER TABLE "Item" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Item" ADD COLUMN "keywords" TEXT;

-- AlterTable
ALTER TABLE "Journal" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Journal" ADD COLUMN "keywords" TEXT;

-- AlterTable
ALTER TABLE "Hook" ADD COLUMN "aliases" TEXT;
ALTER TABLE "Hook" ADD COLUMN "keywords" TEXT;

