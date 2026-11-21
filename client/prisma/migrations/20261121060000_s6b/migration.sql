-- AlterTable
ALTER TABLE "Setting" ADD COLUMN "slug" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "Setting_slug_key" ON "Setting"("slug");
