"use client";

import { MasterDataPage } from "@/components/settings/MasterDataPage";

export default function BrandsSettingsPage() {
  return (
    <MasterDataPage
      resource="brands"
      title="Brands"
      description="The brand an item is sold under"
      singular="Brand"
      placeholder="e.g. Dove"
    />
  );
}
