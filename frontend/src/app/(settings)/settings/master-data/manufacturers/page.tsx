"use client";

import { MasterDataPage } from "@/components/settings/MasterDataPage";

export default function ManufacturersSettingsPage() {
  return (
    <MasterDataPage
      resource="manufacturers"
      title="Manufacturers"
      description="The company that makes an item"
      singular="Manufacturer"
      placeholder="e.g. Unilever"
    />
  );
}
