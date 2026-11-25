import React from 'react';
import { NavLink } from 'react-router-dom';
import { FiHome, FiDollarSign, FiFileText, FiUpload, FiCpu, FiServer, FiChevronLeft } from 'react-icons/fi';

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: FiHome },
  { path: '/reconciliation', label: 'Reconciliation', icon: FiDollarSign },
  { path: '/pricing', label: 'Price Management', icon: FiFileText },
  { path: '/connectors', label: 'Data Ingestion', icon: FiUpload },
  { path: '/ai', label: 'AI Invoice Processing', icon: FiCpu },
  { path: '/hub', label: 'Hub Simulator', icon: FiServer },
];

export default function Sidebar({
  isOpen,
  onClose,
  currentStore,
  stores,
  onStoreChange,
  dateRange,
  onDateRangeChange,
  hubStatus
}) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`} role="navigation" aria-label="Main navigation">
      <div className="sidebar-header">
        <div className="sidebar-logo">B</div>
        <span className="sidebar-title">Brightleaf Retail</span>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <div className="nav-section-title">Analytics</div>
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={onClose}
              end={item.path === '/dashboard'}
            >
              <span className="nav-icon">
                <item.icon size={20} />
              </span>
              {item.label}
            </NavLink>
          ))}
        </div>

        <div className="nav-section">
          <div className="nav-section-title">Store Context</div>
          <div style={{ padding: '0 12px 8px' }}>
            <label className="form-label" style={{ fontSize: '11px' }}>Active Store</label>
            <select
              className="form-select"
              value={currentStore}
              onChange={(e) => onStoreChange(parseInt(e.target.value))}
              style={{ fontSize: '13px', padding: '8px 12px' }}
            >
              {stores.map(store => (
                <option key={store.store_id} value={store.store_id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>

          <div style={{ padding: '0 12px' }}>
            <label className="form-label" style={{ fontSize: '11px' }}>Date Range</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="date"
                className="form-input"
                value={dateRange.start}
                onChange={(e) => onDateRangeChange({ ...dateRange, start: e.target.value })}
                style={{ flex: 1, fontSize: '12px', padding: '8px' }}
              />
              <input
                type="date"
                className="form-input"
                value={dateRange.end}
                onChange={(e) => onDateRangeChange({ ...dateRange, end: e.target.value })}
                style={{ flex: 1, fontSize: '12px', padding: '8px' }}
              />
            </div>
          </div>
        </div>
      </nav>

      <div className="sidebar-footer">
        <div className={`hub-status ${hubStatus.running ? 'running' : ''}`}>
          <span className={`status-dot ${hubStatus.running ? 'running' : ''}`}></span>
          <span>Hub: {hubStatus.running ? 'Running' : 'Stopped'}</span>
          {hubStatus.last_run && (
            <span style={{ marginLeft: 'auto', fontSize: '11px', color: 'var(--text-secondary)' }}>
              Last: {new Date(hubStatus.last_run).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}