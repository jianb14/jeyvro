function I({ size = 18, className, strokeWidth = 1.8, children, ...rest }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const MenuIcon = (p) => <I {...p}><path d="M4 7h16M4 12h16M4 17h16" /></I>;
export const XIcon = (p) => <I {...p}><path d="M6 6l12 12M18 6 6 18" /></I>;
export const SunIcon = (p) => <I {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></I>;
export const MoonIcon = (p) => <I {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></I>;
export const ChevronDownIcon = (p) => <I {...p}><path d="m6 9 6 6 6-6" /></I>;
export const ChevronUpIcon = (p) => <I {...p}><path d="m18 15-6-6-6 6" /></I>;
export const ChevronRightIcon = (p) => <I {...p}><path d="m9 6 6 6-6 6" /></I>;
export const ChevronLeftIcon = (p) => <I {...p}><path d="m15 6-6 6 6 6" /></I>;
export const ChevronsUpDownIcon = (p) => <I {...p}><path d="m7 15 5 5 5-5M7 9l5-5 5 5" /></I>;
export const CheckIcon = (p) => <I {...p}><path d="M5 13l4 4L19 7" /></I>;
export const PlusIcon = (p) => <I {...p}><path d="M12 5v14M5 12h14" /></I>;
export const MinusIcon = (p) => <I {...p}><path d="M5 12h14" /></I>;
export const SearchIcon = (p) => <I {...p}><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></I>;
export const MailIcon = (p) => <I {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></I>;
export const UserIcon = (p) => <I {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" /></I>;
export const CalendarIcon = (p) => <I {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 11h18" /></I>;
export const EyeIcon = (p) => <I {...p}><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></I>;
export const EyeOffIcon = (p) => <I {...p}><path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-2.9 3.9M6.6 6.6C3.7 8.6 2 12 2 12s3.5 7 10 7c1.4 0 2.7-.3 3.8-.8M9.9 9.9a3 3 0 0 0 4.2 4.2" /></I>;
export const AlertCircleIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></I>;
export const AlertTriangleIcon = (p) => <I {...p}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /><path d="M12 9v4M12 17h.01" /></I>;
export const InfoIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></I>;
export const CheckCircleIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="m8.5 12.5 2.5 2.5 5-5.5" /></I>;
export const XCircleIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6M15 9l-6 6" /></I>;
export const CopyIcon = (p) => <I {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></I>;
export const TrashIcon = (p) => <I {...p}><path d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M10 11v6M14 11v6" /></I>;
export const EditIcon = (p) => <I {...p}><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" /></I>;
export const DownloadIcon = (p) => <I {...p}><path d="M12 3v12m-5-5 5 5 5-5M4 21h16" /></I>;
export const ExternalLinkIcon = (p) => <I {...p}><path d="M14 4h6v6M20 4 11 13M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></I>;
export const SettingsIcon = (p) => <I {...p}><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1" /></I>;
export const BellIcon = (p) => <I {...p}><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M10.3 21a2 2 0 0 0 3.4 0" /></I>;
export const LogOutIcon = (p) => <I {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></I>;
export const HeartIcon = (p) => <I {...p}><path d="M19.5 12.6 12 20l-7.5-7.4a5 5 0 1 1 7.5-6.6 5 5 0 1 1 7.5 6.6z" /></I>;
export const StarIcon = (p) => <I {...p}><path d="m12 2.5 2.9 5.9 6.6 1-4.8 4.6 1.1 6.5-5.8-3-5.8 3 1.1-6.5-4.8-4.6 6.6-1z" /></I>;
export const ArrowLeftIcon = (p) => <I {...p}><path d="M20 12H4m6-6-6 6 6 6" /></I>;
export const ArrowRightIcon = (p) => <I {...p}><path d="M4 12h16m-6-6 6 6-6 6" /></I>;
export const ArrowUpRightIcon = (p) => <I {...p}><path d="M7 17 17 7M8 7h9v9" /></I>;
export const MoreHorizontalIcon = (p) => <I {...p}><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></I>;
export const MoreVerticalIcon = (p) => <I {...p}><circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" /></I>;
export const HomeIcon = (p) => <I {...p}><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /><path d="M9 21v-8h6v8" /></I>;
export const GlobeIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></I>;
export const SendIcon = (p) => <I {...p}><path d="m22 2-7 20-4-9-9-4z" /><path d="M22 2 11 13" /></I>;
export const LeafIcon = (p) => <I {...p}><path d="M11 20A7 7 0 0 1 4 13c0-4 3-8 9-9 4.5-.8 7 .5 7 .5S20.5 20 11 20z" /><path d="M4.5 19.5c3-5 6.5-8 11-11" /></I>;
export const GithubIcon = (p) => <I {...p}><path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V19" /></I>;
export const UploadIcon = (p) => <I {...p}><path d="M12 15V3m-5 5 5-5 5 5M4 21h16" /></I>;
export const FileIcon = (p) => <I {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></I>;
export const CornerDownLeftIcon = (p) => <I {...p}><path d="M20 4v7a4 4 0 0 1-4 4H4m5-4-4 4 4 4" /></I>;
export const ZapIcon = (p) => <I {...p}><path d="M13 2 4.1 12.9a.5.5 0 0 0 .4.8H11l-1 8.3 8.9-10.9a.5.5 0 0 0-.4-.8H13z" /></I>;
export const CreditCardIcon = (p) => <I {...p}><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></I>;
export const PackageIcon = (p) => <I {...p}><path d="M21 8v8a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 16V8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0l7 4A2 2 0 0 1 21 8z" /><path d="m3.3 7 8.7 5 8.7-5M12 22V12" /></I>;
export const ClockIcon = (p) => <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></I>;
export const InboxIcon = (p) => <I {...p}><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1z" /></I>;
export const ShoppingCartIcon = (p) => <I {...p}><circle cx="9" cy="20" r="1.6" /><circle cx="17" cy="20" r="1.6" /><path d="M2 3h2.5l2.2 12.4a1.5 1.5 0 0 0 1.5 1.3h8.6a1.5 1.5 0 0 0 1.5-1.2L20 7H5" /></I>;
export const ShoppingBagIcon = (p) => <I {...p}><path d="M6 7h12l1.2 13a1.5 1.5 0 0 1-1.5 1.7H6.3A1.5 1.5 0 0 1 4.8 20z" /><path d="M8.5 10V6.5a3.5 3.5 0 0 1 7 0V10" /></I>;
export const StoreIcon = (p) => <I {...p}><path d="M4 10v9a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-9M2.5 7 4 3h16l1.5 4z" /><path d="M2.5 7h19v1a2.5 2.5 0 0 1-5 0V7M11.5 7v1a2.5 2.5 0 0 1-5 0V7M2.5 7h4v1a2 2 0 1 1-4 0zM17.5 7h4v1a2 2 0 1 1-4 0z" /></I>;
export const MapPinIcon = (p) => <I {...p}><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" /><circle cx="12" cy="10" r="3" /></I>;
export const PhoneIcon = (p) => <I {...p}><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.13.96.36 1.9.7 2.8a2 2 0 0 1-.45 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.45c.9.34 1.84.57 2.8.7A2 2 0 0 1 22 16.9z" /></I>;
export const TruckIcon = (p) => <I {...p}><path d="M14 17V5a1 1 0 0 0-1-1H2v13h2M14 8h4l4 4v5h-2" /><circle cx="6.5" cy="17.5" r="2" /><circle cx="17.5" cy="17.5" r="2" /></I>;
export const ShieldCheckIcon = (p) => <I {...p}><path d="M12 22s8-3.6 8-10V5l-8-3-8 3v7c0 6.4 8 10 8 10z" /><path d="m8.8 11.8 2.2 2.2 4.2-4.5" /></I>;
export const TagIcon = (p) => <I {...p}><path d="M12.6 2.6 21 11a2 2 0 0 1 0 2.8l-7.2 7.2a2 2 0 0 1-2.8 0L2.6 12.6A2 2 0 0 1 2 11.2V4a2 2 0 0 1 2-2h7.2a2 2 0 0 1 1.4.6z" /><circle cx="7.5" cy="7.5" r="1.3" /></I>;
export const FilterIcon = (p) => <I {...p}><path d="M3 5h18M6.5 12h11M10 19h4" /></I>;
export const WalletIcon = (p) => <I {...p}><path d="M20 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z" /><path d="M16 7V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v2M16 14h.01" /></I>;
export const PercentIcon = (p) => <I {...p}><path d="m19 5-14 14" /><circle cx="7" cy="7" r="2.5" /><circle cx="17" cy="17" r="2.5" /></I>;
export const CreditCardSolidIcon = (p) => <I {...p}><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 10h20" /></I>;
export const HeartSolidIcon = ({ size = 18, className }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" className={className} aria-hidden="true">
    <path d="M19.5 12.6 12 20l-7.5-7.4a5 5 0 1 1 7.5-6.6 5 5 0 1 1 7.5 6.6z" />
  </svg>
);

/**
 * Circular verified seal — 10 evenly spaced spikes (the "tusok-tusok" rosette).
 * The path alternates outer tips (radius 10.2) and inner valleys (radius 7.8)
 * every 18° around the exact center (12, 12), so the bounding box stays a
 * perfect 20.4 × 20.4 square and the seal never renders oblong at any size.
 */
export function VerifiedBadgeIcon({ size = 14, className }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className={className} aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 1.8 14.4 4.6 18 3.7 18.3 7.4 21.7 8.8 19.8 12 21.7 15.2 18.3 16.6 18 20.3 14.4 19.4 12 22.2 9.6 19.4 6 20.3 5.7 16.6 2.3 15.2 4.2 12 2.3 8.8 5.7 7.4 6 3.7 9.6 4.6Z"
      />
      <path
        d="m8.1 12.4 2.8 2.8 5.5-5.7"
        fill="none"
        className="stroke-white"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LogoMark({ size = 28, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="#4f6d3f" />
      <path d="M23.5 8.5C17 8.5 10 12 9.5 23.5 21 23 24 16 23.5 8.5Z" fill="#ffffff" />
      <path d="M11 21.5C14 17 18 13.5 22 10.5" stroke="#4f6d3f" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
