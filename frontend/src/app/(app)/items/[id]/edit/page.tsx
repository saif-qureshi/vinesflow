"use client";

import { useParams } from "next/navigation";

import { errorState, loadingState, notFoundState } from "@/components/ui/QueryFallback";

import { ItemForm } from "../../ItemForm";
import { useProduct } from "@/hooks/useProducts";

export default function EditItemPage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading, error } = useProduct(Number(id));

  if (error) return errorState(error);
  if (isLoading) return loadingState();
  if (!data) return notFoundState();

  return <ItemForm key={data.id} product={data} />;
}
