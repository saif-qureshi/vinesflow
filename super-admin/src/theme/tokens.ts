import type { ThemeConfig } from "antd";
import { theme } from "antd";

export const brand = {
  primary: "#0f766e",
  primaryHover: "#115e59",
  secondary: "#0f766e",
  sidebarBg: "#0f172a",
  sidebarText: "#cbd5e1",
  muted: "#94a3b8",
  surface: "#f8fafc",
  border: "#e2e8f0",
} as const;

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: brand.primary,
    colorLink: brand.primary,
    borderRadius: 6,
    fontSize: 14,
    controlHeight: 38,
    fontFamily: "var(--font-geist-sans), system-ui, sans-serif",
  },
  components: {
    Layout: { siderBg: "#ffffff", headerBg: "#ffffff", bodyBg: brand.surface, headerHeight: 60 },
    Menu: {
      itemColor: "#475569",
      itemSelectedBg: `${brand.primary}1f`,
      itemSelectedColor: brand.primary,
      itemHoverBg: "#f1f5f9",
      itemBorderRadius: 8,
      itemMarginInline: 8,
    },
    Button: { controlHeight: 38 },
    Input: { controlHeight: 38 },
  },
  algorithm: theme.defaultAlgorithm,
};
