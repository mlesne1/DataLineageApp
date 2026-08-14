import React from 'react';

const base = { width: 14, height: 14, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };

export const ChevronIcon = ({ open }) => (
  <svg {...base} style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s ease' }}>
    <polyline points="9 6 15 12 9 18" />
  </svg>
);

export const SearchIcon = () => (
  <svg {...base}>
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

export const CheckIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#0b0f1a" strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export const WarningIcon = () => (
  <svg {...base}>
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export const UploadIcon = () => (
  <svg {...base}>
    <path d="M12 19V5" />
    <path d="M5 12l7-7 7 7" />
  </svg>
);

export const PanelIcon = () => (
  <svg {...base}>
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <line x1="15" y1="4" x2="15" y2="20" />
  </svg>
);

export const CloseIcon = () => (
  <svg {...base}>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

export const EyeIcon = ({ off }) =>
  off ? (
    <svg {...base}>
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.4 19.4 0 0 1 4.22-5.94M9.9 4.24A10.4 10.4 0 0 1 12 4c7 0 11 8 11 8a19.5 19.5 0 0 1-2.16 3.19" />
      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  ) : (
    <svg {...base}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );

export const GridIcon = () => (
  <svg {...base}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
);

export const ClearIcon = () => (
  <svg {...base}>
    <circle cx="12" cy="12" r="9" />
    <line x1="6.5" y1="17.5" x2="17.5" y2="6.5" />
  </svg>
);

export const CaretIcon = () => (
  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);
