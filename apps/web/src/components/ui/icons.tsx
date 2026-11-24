import {
  IconAlertTriangle,
  IconArrowRight,
  IconBell,
  IconCalendar,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconClockHour4,
  IconDeviceMobile,
  IconDownload,
  IconFingerprint,
  IconGavel,
  IconHistory,
  IconInfoCircle,
  IconMenu2,
  IconPhone,
  IconPlus,
  IconScale,
  IconSearch,
  IconShieldCheck,
  IconUpload,
  IconUser,
  IconX,
  type Icon as TablerIcon,
  type IconProps as TablerIconProps,
} from "@tabler/icons-react";

/**
 * The Figma icon set is Tabler, drawn at 1.75 stroke on the 24 grid
 * (0.875 at 12px, 1.167 at 16px). Only icons used on the December screens
 * are exported here.
 */
export const ICON_STROKE = 1.75;

export type IconName =
  | "alert-triangle"
  | "arrow-right"
  | "bell"
  | "calendar"
  | "check"
  | "chevron-down"
  | "chevron-right"
  | "clock-hour-4"
  | "device-mobile"
  | "download"
  | "fingerprint"
  | "gavel"
  | "history"
  | "info-circle"
  | "menu-2"
  | "phone"
  | "plus"
  | "scale"
  | "search"
  | "shield-check"
  | "upload"
  | "user"
  | "x";

const ICONS: Record<IconName, TablerIcon> = {
  "alert-triangle": IconAlertTriangle,
  "arrow-right": IconArrowRight,
  bell: IconBell,
  calendar: IconCalendar,
  check: IconCheck,
  "chevron-down": IconChevronDown,
  "chevron-right": IconChevronRight,
  "clock-hour-4": IconClockHour4,
  "device-mobile": IconDeviceMobile,
  download: IconDownload,
  fingerprint: IconFingerprint,
  gavel: IconGavel,
  history: IconHistory,
  "info-circle": IconInfoCircle,
  "menu-2": IconMenu2,
  phone: IconPhone,
  plus: IconPlus,
  scale: IconScale,
  search: IconSearch,
  "shield-check": IconShieldCheck,
  upload: IconUpload,
  user: IconUser,
  x: IconX,
};

export const ICON_NAMES = Object.keys(ICONS) as IconName[];

type IconProps = Omit<TablerIconProps, "ref"> & {
  name: IconName;
  /** Accessible name. Without it the icon is decorative and hidden. */
  label?: string;
};

export function Icon({ name, label, size = 16, stroke = ICON_STROKE, ...rest }: IconProps) {
  const Component = ICONS[name];
  return (
    <Component
      size={size}
      stroke={stroke}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? "img" : undefined}
      focusable={false}
      {...rest}
    />
  );
}
