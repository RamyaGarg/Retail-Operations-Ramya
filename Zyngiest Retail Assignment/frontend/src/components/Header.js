import React from 'react';
import { FiMenu, FiCalendar, FiDownload } from 'react-icons/fi';

export default function Header({
  pageTitle,
  currentStore,
  onMenuClick,
  dateRange,
  onDateRangeChange
}) {
  return (
    <header className="header" role="banner">
      <div className="header-left">
        <button
          className="mobile-menu-toggle"
          onClick={onMenuClick}
          aria-label="Toggle menu"
          aria-expanded="false"
        >
          <FiMenu size={24} />
        </button>
        <div>
          <h1 className="page-title">{pageTitle}</h1>
          {currentStore && (
            <div className="breadcrumb">
              <span>{currentStore.name}</span>
              <span className="breadcrumb-separator">/</span>
              <span>{currentStore.location}</span>
            </div>
          )}
        </div>
      </div>

      <div className="header-right">
        <div className="date-range-picker">
          <FiCalendar size={16} />
          <span>
            {formatDate(dateRange.start)} - {formatDate(dateRange.end)}
          </span>
        </div>

        <select className="store-selector" defaultValue={currentStore?.store_id}>
          <option value={1}>Brightleaf Downtown</option>
          <option value={2}>Brightleaf Mall</option>
        </select>
      </div>
    </header>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}