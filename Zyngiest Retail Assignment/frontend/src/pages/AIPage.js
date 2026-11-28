import React, { useState, useEffect } from 'react';
import { aiApi } from '../api/client';
import { FiUpload, FiFileText, FiCheckCircle, FiAlertTriangle, FiEye, FiRefreshCw, FiDollarSign, FiPackage, FiX } from 'react-icons/fi';

export default function AIPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [matchPO, setMatchPO] = useState('');

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    setLoading(true);
    try {
      // Get from outbox files - in real app, would have dedicated endpoint
      // For now, show placeholder
      setInvoices([
        { id: 'INV_20240115_1234', supplier: 'Brightleaf Wholesale', date: '2024-01-15', total: '410.40', status: 'completed', confidence: 0.92 },
        { id: 'INV_20240114_5678', supplier: 'Fresh Foods Ltd', date: '2024-01-14', total: '235.80', status: 'completed', confidence: 0.88 },
        { id: 'INV_20240113_9012', supplier: 'Beverage Co', date: '2024-01-13', total: '567.20', status: 'failed', confidence: 0.0 },
      ]);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadStatus({ type: 'info', message: `Processing ${file.name} with AI...` });

    try {
      const res = await aiApi.processInvoice(file);
      setUploadStatus({
        type: res.data.status === 'completed' ? 'success' : 'danger',
        message: `AI Processing: ${res.data.status} (Confidence: ${Math.round(res.data.confidence * 100)}%)`,
      });
      loadInvoices();
    } catch (err) {
      setUploadStatus({
        type: 'danger',
        message: `Processing failed: ${err.response?.data?.detail || err.message}`,
      });
    }
  };

  const handleProcessInbox = async () => {
    setUploadStatus({ type: 'info', message: 'Processing inbox invoices...' });
    try {
      const res = await aiApi.processInboxInvoices();
      setUploadStatus({
        type: 'success',
        message: `Processed ${res.data.results.length} invoices from inbox`,
      });
      loadInvoices();
    } catch (err) {
      setUploadStatus({ type: 'danger', message: err.message });
    }
  };

  const handleViewDetails = async (invoiceId) => {
    try {
      const res = await aiApi.getExtractedData(invoiceId);
      setSelectedInvoice(res.data);
      setShowModal(true);
    } catch (err) {
      alert('Failed to load invoice details: ' + err.message);
    }
  };

  const handleMatchPO = async () => {
    if (!selectedInvoice || !matchPO) return;
    try {
      await aiApi.matchInvoiceToPO(selectedInvoice.invoice_id, matchPO);
      alert('Invoice matched to PO successfully');
      setMatchPO('');
    } catch (err) {
      alert('Matching failed: ' + err.message);
    }
  };

  const handleCreateGoodsReceipt = async () => {
    if (!selectedInvoice?.items) return;

    const receivedItems = selectedInvoice.items.map(item => ({
      item_code: item.description.replace(/\s+/g, '_').toUpperCase(),
      variant_code: 'DEFAULT',
      quantity: item.quantity,
    }));

    try {
      const res = await aiApi.createGoodsReceipt(selectedInvoice.invoice_id, receivedItems);
      alert(`Goods receipt created: ${res.data.receipt_id}`);
    } catch (err) {
      alert('Failed to create goods receipt: ' + err.message);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 600 }}>AI Invoice Processing</h2>
        <button className="btn btn-primary" onClick={handleProcessInbox}>
          <FiRefreshCw size={16} /> Process Inbox
        </button>
      </div>

      {/* Upload Zone */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h3 className="card-title">Upload Invoice for AI Extraction</h3>
        </div>
        <div className="card-body">
          <div style={{
            border: '2px dashed var(--border)',
            borderRadius: 'var(--radius)',
            padding: '40px',
            textAlign: 'center',
            background: 'var(--background)',
          }}>
            <FiUpload size={36} style={{ color: 'var(--primary)', marginBottom: '12px' }} />
            <h3 style={{ marginBottom: '8px' }}>Drag & Drop or Click to Upload</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Supports: PDF, XML, PNG, JPG, TIFF
            </p>
            <label className="btn btn-primary">
              Select File
              <input type="file" accept=".pdf,.xml,.png,.jpg,.jpeg,.tiff" onChange={handleFileUpload} style={{ display: 'none' }} />
            </label>

            {uploadStatus && (
              <div className={`badge badge-${uploadStatus.type}`} style={{ marginTop: '16px', fontSize: '13px' }}>
                {uploadStatus.message}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Processed Invoices */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Processed Invoices</h2>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {loading ? (
            <div className="loading" style={{ padding: '40px' }}><div className="spinner"></div></div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Invoice ID</th>
                    <th>Supplier</th>
                    <th>Date</th>
                    <th>Total</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(inv => (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 600, fontFamily: 'monospace' }}>{inv.id}</td>
                      <td>{inv.supplier}</td>
                      <td>{inv.date}</td>
                      <td style={{ fontWeight: 600 }}>£{formatCurrency(inv.total)}</td>
                      <td>
                        <span className={`badge badge-${inv.status === 'completed' ? 'success' : 'danger'}`}>
                          {inv.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '80px', height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{
                              width: `${inv.confidence * 100}%`,
                              height: '100%',
                              background: inv.confidence > 0.8 ? 'var(--success)' : inv.confidence > 0.5 ? 'var(--warning)' : 'var(--danger)',
                            }} />
                          </div>
                          <span style={{ fontSize: '12px' }}>{Math.round(inv.confidence * 100)}%</span>
                        </div>
                      </td>
                      <td>
                        {inv.status === 'completed' && (
                          <button className="btn btn-secondary btn-sm" onClick={() => handleViewDetails(inv.id)}>
                            <FiEye size={14} /> View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Invoice Detail Modal */}
      {showModal && selectedInvoice && (
        <div className="modal-overlay">
          <div className="modal" style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Invoice Details: {selectedInvoice.invoice_number}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}><FiX size={18} /></button>
            </div>
            <div className="modal-body">
              {/* Header Info */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '24px', padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Supplier</div>
                  <div style={{ fontWeight: 600 }}>{selectedInvoice.supplier}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Invoice Number</div>
                  <div style={{ fontWeight: 600 }}>{selectedInvoice.invoice_number}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Invoice Date</div>
                  <div>{selectedInvoice.invoice_date}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Due Date</div>
                  <div>{selectedInvoice.due_date}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Subtotal</div>
                  <div>£{formatCurrency(selectedInvoice.subtotal)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Tax</div>
                  <div>£{formatCurrency(selectedInvoice.tax_total)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total</div>
                  <div style={{ fontWeight: 700, fontSize: '18px' }}>£{formatCurrency(selectedInvoice.grand_total)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Currency</div>
                  <div>{selectedInvoice.currency}</div>
                </div>
              </div>

              {/* Items Table */}
              <h4 style={{ marginBottom: '12px' }}>Line Items</h4>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Unit Price</th>
                      <th>Line Total</th>
                      <th>Tax Group</th>
                      <th>Tax Amt</th>
                      <th>Department</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedInvoice.items.map(item => (
                      <tr key={item.line_number}>
                        <td>{item.line_number}</td>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>£{formatCurrency(item.unit_price)}</td>
                        <td style={{ fontWeight: 600 }}>£{formatCurrency(item.line_total)}</td>
                        <td>{item.tax_group}</td>
                        <td>£{formatCurrency(item.tax_amount)}</td>
                        <td>{item.department}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* PO Matching */}
              <div style={{ marginTop: '24px', padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
                <h4 style={{ marginBottom: '12px' }}>Purchase Order Matching</h4>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Enter PO Number"
                    value={matchPO}
                    onChange={(e) => setMatchPO(e.target.value)}
                    style={{ maxWidth: '200px' }}
                  />
                  <button className="btn btn-primary" onClick={handleMatchPO} disabled={!matchPO}>
                    Match to PO
                  </button>
                  <button className="btn btn-secondary" onClick={handleCreateGoodsReceipt}>
                    <FiPackage size={14} /> Create Goods Receipt
                  </button>
                </div>
              </div>

              {/* Raw Text */}
              {selectedInvoice.raw_text && (
                <details style={{ marginTop: '24px' }}>
                  <summary style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>Raw OCR Text</summary>
                  <pre style={{ marginTop: '8px', padding: '12px', background: '#1a1a1a', color: '#e0e0e0', borderRadius: 'var(--radius)', fontSize: '12px', overflow: 'auto', maxHeight: '200px' }}>
                    {selectedInvoice.raw_text}
                  </pre>
                </details>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatCurrency(val) {
  return parseFloat(val).toFixed(2);
}