import React, { useState, useEffect } from 'react';
import { hubApi } from '../api/client';
import { FiRefreshCw, FiSend, FiInbox, FiSettings, FiServer, FiActivity, FiCheckCircle, FiAlertTriangle, FiClock } from 'react-icons/fi';

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getStatusBadge = (status) => {
  const badges = {
    pending: 'badge-pending',
    processing: 'badge-warning',
    completed: 'badge-success',
    failed: 'badge-danger',
  };
  return <span className={`badge ${badges[status] || 'badge-pending'}`}>{status}</span>;
};

export default function HubPage() {
  const [activeTab, setActiveTab] = useState('overview'); // overview, inbox, outbox, config
  const [overview, setOverview] = useState(null);
  const [inboxFiles, setInboxFiles] = useState([]);
  const [outboxFiles, setOutboxFiles] = useState([]);
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [workerStatus, setWorkerStatus] = useState('unknown');
  const [lastProcessed, setLastProcessed] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [ovRes, inboxRes, outboxRes, configRes] = await Promise.all([
        hubApi.getHubOverview(),
        hubApi.getInboxFiles(),
        hubApi.getOutboxFiles(),
        hubApi.getHubConfig(),
      ]);

      setOverview(ovRes.data);
      setInboxFiles(inboxRes.data.files || []);
      setOutboxFiles(outboxRes.data.files || []);
      setConfig(configRes.data);
      setWorkerStatus(ovRes.data.worker_status || 'unknown');
      setLastProcessed(ovRes.data.last_processed);
    } catch (err) {
      console.error('Failed to load hub data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessInbox = async () => {
    try {
      const res = await hubApi.processInbox();
      alert(`Processed ${res.data.processed_count} files from inbox`);
      loadData();
    } catch (err) {
      alert('Failed to process inbox: ' + err.message);
    }
  };

  const handleSimulateStoreSubmission = async () => {
    try {
      const res = await hubApi.simulateStoreSubmission();
      alert(`Simulated store submission: ${res.data.filename}`);
      loadData();
    } catch (err) {
      alert('Failed to simulate submission: ' + err.message);
    }
  };

  const handleProcessStoreOutbox = async () => {
    try {
      const res = await hubApi.processStoreOutbox();
      alert(`Processed ${res.data.processed_count} files for store`);
      loadData();
    } catch (err) {
      alert('Failed to process store outbox: ' + err.message);
    }
  };

  const handleUpdateConfig = async () => {
    try {
      await hubApi.updateHubConfig(config);
      alert('Configuration updated');
      loadData();
    } catch (err) {
      alert('Failed to update config: ' + err.message);
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: 600 }}>Hub Simulator</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
            Central hub for store data exchange and price list distribution
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={handleProcessInbox} disabled={loading}>
            <FiRefreshCw size={16} /> Process Inbox
          </button>
          <button className="btn btn-secondary" onClick={handleSimulateStoreSubmission} disabled={loading}>
            <FiSend size={16} /> Simulate Store Submission
          </button>
          <button className="btn btn-secondary" onClick={handleProcessStoreOutbox} disabled={loading}>
            <FiInbox size={16} /> Process Store Outbox
          </button>
        </div>
      </div>

      {/* Worker Status Bar */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`status-dot ${workerStatus === 'running' ? 'status-running' : 'status-stopped'}`}></span>
              <strong>Worker: {workerStatus.charAt(0).toUpperCase() + workerStatus.slice(1)}</strong>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Poll Interval: {config.poll_interval_seconds || 10}s
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Max Retries: {config.max_retries || 3}
            </div>
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            Last Processed: {lastProcessed ? new Date(lastProcessed).toLocaleString() : 'Never'}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
        <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
          <FiServer size={14} /> Overview
        </TabButton>
        <TabButton active={activeTab === 'inbox'} onClick={() => setActiveTab('inbox')}>
          <FiInbox size={14} /> Inbox ({inboxFiles.length})
        </TabButton>
        <TabButton active={activeTab === 'outbox'} onClick={() => setActiveTab('outbox')}>
          <FiSend size={14} /> Outbox ({outboxFiles.length})
        </TabButton>
        <TabButton active={activeTab === 'config'} onClick={() => setActiveTab('config')}>
          <FiSettings size={14} /> Configuration
        </TabButton>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner"></div></div>
      ) : (
        <>
          {activeTab === 'overview' && <OverviewTab overview={overview} />}
          {activeTab === 'inbox' && <InboxTab files={inboxFiles} />}
          {activeTab === 'outbox' && <OutboxTab files={outboxFiles} />}
          {activeTab === 'config' && <ConfigTab config={config} onSave={handleUpdateConfig} />}
        </>
      )}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '8px 16px',
        borderRadius: 'var(--radius)',
        fontSize: '14px',
        fontWeight: 500,
        background: active ? 'var(--primary)' : 'transparent',
        color: active ? 'white' : 'var(--text-secondary)',
        transition: 'all 0.2s',
      }}
    >
      {children}
    </button>
  );
}

function OverviewTab({ overview }) {
  if (!overview) return <div>Loading...</div>;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
      {/* Stats Cards */}
      <StatCard
        title="Inbox Files Pending"
        value={overview.inbox_pending || 0}
        icon={<FiInbox size={24} />}
        color="#1a5f7a"
      />
      <StatCard
        title="Outbox Files Ready"
        value={overview.outbox_ready || 0}
        icon={<FiSend size={24} />}
        color="#2e8b7a"
      />
      <StatCard
        title="Processed Today"
        value={overview.processed_today || 0}
        icon={<FiCheckCircle size={24} />}
        color="#d4a52a"
      />
      <StatCard
        title="Failed Items"
        value={overview.failed_today || 0}
        icon={<FiAlertTriangle size={24} />}
        color="#e74c3c"
      />

      {/* Directory Structure */}
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <div className="card-header">
          <h2 className="card-title">Directory Structure</h2>
        </div>
        <div className="card-body">
          <div style={{ fontFamily: 'monospace', fontSize: '13px', lineHeight: '2' }}>
            {overview.directories?.map((dir, i) => (
              <div key={i} style={{ paddingLeft: `${(dir.depth || 0) * 20}px` }}>
                <span style={{ color: dir.type === 'directory' ? 'var(--primary)' : 'var(--text-secondary)' }}>
                  {dir.type === 'directory' ? '📁' : '📄'} {dir.name}
                </span>
                {dir.file_count !== undefined && (
                  <span style={{ color: 'var(--text-secondary)', marginLeft: '12px' }}>
                    ({dir.file_count} files)
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <div className="card-header">
          <h2 className="card-title">Recent Hub Activity</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Filename</th>
                  <th>Store</th>
                  <th>Status</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {overview.recent_activity?.map((act, i) => (
                  <tr key={i}>
                    <td>{new Date(act.timestamp).toLocaleTimeString()}</td>
                    <td style={{ textTransform: 'capitalize' }}>{act.action}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>{act.filename}</td>
                    <td>{act.store_id || '—'}</td>
                    <td>{getStatusBadge(act.status)}</td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>{act.details || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function InboxTab({ files }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Inbox Files (Pending Processing)</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        {files.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <FiInbox size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>No files in inbox</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Received</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {files.map(f => (
                  <tr key={f.name}>
                    <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>{f.name}</td>
                    <td style={{ textTransform: 'uppercase' }}>{f.type}</td>
                    <td>{formatFileSize(f.size)}</td>
                    <td>{new Date(f.received_at).toLocaleString()}</td>
                    <td>{getStatusBadge(f.status)}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" disabled={f.status !== 'pending'}>
                        <FiActivity size={12} /> Process
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function OutboxTab({ files }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Outbox Files (Ready for Store Pickup)</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        {files.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <FiSend size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>No files in outbox</p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>For Store</th>
                </tr>
              </thead>
              <tbody>
                {files.map(f => (
                  <tr key={f.name}>
                    <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>{f.name}</td>
                    <td style={{ textTransform: 'uppercase' }}>{f.type}</td>
                    <td>{formatFileSize(f.size)}</td>
                    <td>{new Date(f.created_at).toLocaleString()}</td>
                    <td>{getStatusBadge(f.status)}</td>
                    <td>{f.for_store || 'All'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function ConfigTab({ config, onSave }) {
  const [localConfig, setLocalConfig] = useState(config);

  useEffect(() => {
    setLocalConfig(config);
  }, [config]);

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Hub Configuration</h2>
      </div>
      <div className="card-body">
        <form onSubmit={(e) => { e.preventDefault(); onSave(); }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
            <ConfigField
              label="Hub ID"
              name="hub_id"
              value={localConfig.hub_id}
              onChange={(v) => setLocalConfig({ ...localConfig, hub_id: v })}
              type="text"
              disabled
            />
            <ConfigField
              label="Poll Interval (seconds)"
              name="poll_interval_seconds"
              value={localConfig.poll_interval_seconds}
              onChange={(v) => setLocalConfig({ ...localConfig, poll_interval_seconds: parseInt(v) })}
              type="number"
              min="1"
            />
            <ConfigField
              label="Max Retries"
              name="max_retries"
              value={localConfig.max_retries}
              onChange={(v) => setLocalConfig({ ...localConfig, max_retries: parseInt(v) })}
              type="number"
              min="0"
            />
            <ConfigField
              label="Retry Delay (seconds)"
              name="retry_delay_seconds"
              value={localConfig.retry_delay_seconds}
              onChange={(v) => setLocalConfig({ ...localConfig, retry_delay_seconds: parseInt(v) })}
              type="number"
              min="1"
            />
            <ConfigField
              label="Inbox Path"
              name="inbox_path"
              value={localConfig.inbox_path}
              onChange={(v) => setLocalConfig({ ...localConfig, inbox_path: v })}
              type="text"
            />
            <ConfigField
              label="Outbox Path"
              name="outbox_path"
              value={localConfig.outbox_path}
              onChange={(v) => setLocalConfig({ ...localConfig, outbox_path: v })}
              type="text"
            />
            <ConfigField
              label="Store Inbox Path"
              name="store_inbox_path"
              value={localConfig.store_inbox_path}
              onChange={(v) => setLocalConfig({ ...localConfig, store_inbox_path: v })}
              type="text"
            />
            <ConfigField
              label="Store Outbox Path"
              name="store_outbox_path"
              value={localConfig.store_outbox_path}
              onChange={(v) => setLocalConfig({ ...localConfig, store_outbox_path: v })}
              type="text"
            />
          </div>

          <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
            <button type="submit" className="btn btn-primary">
              <FiCheckCircle size={14} /> Save Configuration
            </button>
          </div>
        </form>

        <div style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--border)' }}>
          <h3 style={{ marginBottom: '16px' }}>Current Paths (Resolved)</h3>
          <div style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '2' }}>
            <div>Inbox: {localConfig.inbox_path}</div>
            <div>Outbox: {localConfig.outbox_path}</div>
            <div>Store Inbox: {localConfig.store_inbox_path}</div>
            <div>Store Outbox: {localConfig.store_outbox_path}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  return (
    <div className="kpi-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span className="kpi-label">{title}</span>
        <span style={{ color, display: 'flex', alignItems: 'center' }}>{icon}</span>
      </div>
      <div className="kpi-value" style={{ fontSize: '32px' }}>{value}</div>
    </div>
  );
}

function ConfigField({ label, name, value, onChange, type = 'text', min, max, disabled }) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <input
        type={type}
        className="form-input"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        min={min}
        max={max}
        disabled={disabled}
      />
    </div>
  );
}