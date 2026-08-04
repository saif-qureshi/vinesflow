"use client";

import { useParams } from "next/navigation";

import { PartyView } from "@/components/parties/PartyView";

export default function PartyViewPage() {
  const { id } = useParams<{ id: string }>();
  return <PartyView id={Number(id)} />;
}
