import React, { useState, useEffect } from 'react';
import { connectorsApi } from '../api/client';
import { FiUpload, FiFileText, FiCheckCircle, FiXCircle, FiRefreshCw } from 'react-icons/fi';

export default function ConnectorsPage() {
  const [imports, setImports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadStatus, setUploadStatus] = useState(null);

  useEffect(() => {
    loadImports();
  }, []);

  const loadImports = async () => {
    setLoading(true);
    try {
      const res = await connectorsApi.getImports();
      setImports(res.data);
    } catch (err) {
      console.error('Failed to load imports:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadStatus({ type: 'info', message: `Uploading ${file.name}...` });

    try {
      let res;
      if (type === 'xml') {
        res = await connectorsApi.importTLogXML(file);
      } else if (type === 'json') {
        res = await connectorsApi.importTLogJSON(file);
      } else if (type === 'price') {
        res = await connectorsApi.importPriceList(file);
      }

      setUploadStatus({
        type: 'success',
        message: `Successfully processed ${file.name}: ${res.data.records_processed || res.data.message || 'Done'}`,
      });
      loadImports();
    } catch (err) {
      setUploadStatus({
        type: 'danger',
        message: `Upload failed: ${err.response?.data?.detail || err.message}`,
      });
    }
  };

  return (
    <div>
      {/* File Upload Section */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h2 className="card-title">Upload & Process Outbox / Ingestion Files</h2>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            <UploadBox
              title="Transaction Log (XML v2)"
              desc="Upload XML v2 TLOG files from store POS devices"
              accept=".xml"
              onUpload={(e) => handleFileUpload(e, 'xml')}
            />
            <UploadBox
              title="Transaction Log (JSON v3)"
              desc="Upload JSON v3 TLOG files from next-gen devices"
              accept=".json"
              onUpload={(e) => handleFileUpload(e, 'json')}
            />
            <UploadBox
              title="Price List (XML v2)"
              desc="Import master price list from central hub"
              accept=".xml"
              onUpload={(e) => handleFileUpload(e, 'price')}
            />
          </div>

          {uploadStatus && (
            <div className={`badge badge-${uploadStatus.type}`} style={{ marginTop: '16px', padding: '12px 16px', width: '100%', fontSize: '13px' }}>
              {uploadStatus.message}
            </div>
          )}
        </div>
      </div>

      {/* Import History Table */}
      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="card-title">Data Ingestion History</h2>
          <button className="btn btn-secondary btn-sm" onClick={loadImports}>
            <FiRefreshCw size={14} /> Refresh
          </button>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="loading"><div className="spinner"></div></div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Format</th>
                    <th>Version</th>
                    <th>Records</th>
                    <th>Status</th>
                    <th>Imported At</th>
                  </tr>
                </thead>
                <tbody>
                  {imports.map(imp => (
                    <tr key={imp.id}>
                      <td style={{ fontWeight: 600 }}>{imp.filename}</td>
                      <td style={{ textTransform: 'uppercase' }}>{imp.file_format}</td>
                      <td>v{imp.schema_version}</td>
                      <td>{imp.records_processed}</td>
                      <td>
                        <span className={`badge badge-${imp.status === 'SUCCESS' ? 'success' : 'danger'}`}>
                          {imp.status}
                        </span>
                      </td>
                      <td>{new Date(imp.imp_created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function UploadBox({ title, desc, accept, onUpload }) {
  return (
    <div style={{
      border: '2px dashed var(--border)',
      borderRadius: 'var(--radius)',
      padding: '20px',
      textAlign: 'center',
      background: 'var(--background)',
      transition: 'all 0.2s',
    }}>
      <FiUpload size={28} style={{ color: 'var(--primary)', marginBottom: '8px' }} />
      <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '4px' }}>{title}</h3>
      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>{desc}</p>
      <label className="btn btn-primary btn-sm" style={{ cursor: 'pointer', display: 'inline-block' }}>
        Browse File
        <input type="file" accept={accept} onChange={onUpload} style={{ display: 'none' }} />
      </label>
    </div>
  );
}