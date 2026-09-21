import type { EquipmentStatus } from "../types/equipment";

interface StatusStyle {
  label: string;
  color: string;
  bg: string;
}

const STATUS_STYLE: Record<EquipmentStatus, StatusStyle> = {
  normal: { label: "정상", color: "#1B8A5A", bg: "#E4F3EA" },
  review: { label: "교체검토", color: "#D98C00", bg: "#FCEFD8" },
  replace: { label: "즉시교체", color: "#C4392B", bg: "#FBE7E4" },
};

export function statusLabel(status: EquipmentStatus): string {
  return STATUS_STYLE[status].label;
}

export function statusColor(status: EquipmentStatus): string {
  return STATUS_STYLE[status].color;
}

export function statusBg(status: EquipmentStatus): string {
  return STATUS_STYLE[status].bg;
}
