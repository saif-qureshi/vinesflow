export const PK_PROVINCES = [
  { value: "PUNJAB", label: "Punjab" },
  { value: "SINDH", label: "Sindh" },
  { value: "KHYBER PAKHTUNKHWA", label: "Khyber Pakhtunkhwa" },
  { value: "BALOCHISTAN", label: "Balochistan" },
  { value: "CAPITAL TERRITORY", label: "Capital Territory" },
  { value: "GILGIT BALTISTAN", label: "Gilgit Baltistan" },
  { value: "AZAD JAMMU AND KASHMIR", label: "Azad Jammu and Kashmir" },
];

export function isPakistan(country?: string | null): boolean {
  return !country || /^pk$/i.test(country) || /pakistan/i.test(country);
}
