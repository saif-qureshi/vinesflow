export function fbrSalesTax(rateLabel: string | null | undefined, net: number, qty: number): number {
  if (!rateLabel) return 0;
  const value = parseFloat(rateLabel.replace(/[^0-9.]/g, "")) || 0;
  if (rateLabel.includes("%")) return (net * value) / 100;
  if (/rs/i.test(rateLabel)) return value * qty;
  return 0;
}

export function fbrFurtherTax(registered: boolean, net: number): number {
  return registered ? 0 : (net * 3) / 100;
}
