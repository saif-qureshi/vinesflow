export const FBR_SCENARIOS = Array.from({ length: 28 }, (_, i) => {
  const code = `SN${String(i + 1).padStart(3, "0")}`;
  return { value: code, label: code };
});
