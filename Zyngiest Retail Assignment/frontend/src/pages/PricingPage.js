import React, { useState, useEffect } from 'react';
import { pricingApi } from '../api/client';
import { FiPlus, FiCheck, FiX, FiDownload, FiRefreshCw, FiEdit2 } from 'react-icons/fi';

export default function PricingPage({ storeId, dateRange }) {
  const [activeTab, setActiveTab] = useState('list'); // 'list', 'changes'
  const [priceList, setPriceList] = useState([]);
  const [priceChanges, setPriceChanges] = useState([]);
  const [loading, setLoading] = useState(true);

  // New Price Change Modal state
  const [showModal, setShowModal] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [newPrice, setNewPrice] = useState('');
  const [reason, setReason] = useState('');

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'list') {
        const res = await pricingApi.getPriceList();
        setPriceList(res.data);
      } else {
        const res = await pricingApi.getPriceChanges();
        setPriceChanges(res.data);
      }
    } catch (err) {
      console.error('Failed to load pricing data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreatePriceChange = async (e) => {
    e.preventDefault();
    if (!selectedItem || !newPrice) return;

    try {
      await pricingApi.createPriceChange({
        item_code: selectedItem.item_code,
        variant_code: selectedItem.variant_code,
        new_price: newPrice,
        reason: reason || 'Manual price adjustment',
      });
      setShowModal(false);
      setSelectedItem(null);
      setNewPrice('');
      setReason('');
      loadData();
    } catch (err) {
      alert('Failed to create price change: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleApprove = async (changeId) => {
    try {
      await pricingApi.approvePriceChange(changeId);
      await pricingApi.sendAcknowledgement(changeId, 'APPLIED');
      loadData();
    } catch (err) {
      alert('Failed to approve price change: ' + err.message);
    }
  };

  const handleReject = async (changeId) => {
    try {
      await pricingApi.rejectPriceChange(changeId, 'Rejected by manager');
      await pricingApi.sendAcknowledgement(changeId, 'REJECTED');
      loadData();
    } catch (err) {
      alert('Failed to reject price change: ' + err.message);
    }
  };

  const handleExportPriceList = async () => {
    try {
      const res = await pricingApi.exportPriceList();
      alert(`Price list exported successfully: ${res.data.filename}`);
    } catch (err) {
      alert('Export failed: ' + err.message);
    }
  };

  const handleProcessInbox = async () => {
    try {
      const res = await pricingApi.processInboxPriceChanges();
      alert(`Processed ${res.data.results.length} price change files from inbox`);
      loadData();
    } catch (err) {
      alert('Processing failed: ' + err.message);
    }
  };

  return (
    <div>
      {/* Header Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn ${activeTab === 'list' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('list')}
          >
            Item Price List
          </button>
          <button
            className={`btn ${activeTab === 'changes' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('changes')}
          >
            Price Changes
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={handleProcessInbox}>
            <FiRefreshCw size={16} /> Process Inbox Files
          </button>
          <button className="btn btn-secondary" onClick={handleExportPriceList}>
            <FiDownload size={16} /> Export Price List (XML v2)
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner"></div></div>
      ) : activeTab === 'list' ? (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Master Price List</h2>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Item Code</th>
                    <th>Variant</th>
                    <th>Description</th>
                    <th>Department</th>
                    <th>Price</th>
                    <th>Tax Group</th>
                    <th>Age Restrict</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {priceList.map(item => (
                    <tr key={`${item.item_code}_${item.variant_code}`}>
                      <td style={{ fontWeight: 600 }}>{item.item_code}</td>
                      <td>{item.variant_code}</td>
                      <td>{item.description}</td>
                      <td>{item.department_name}</td>
                      <td style={{ fontWeight: 700 }}>£{parseFloat(item.price).toFixed(2)}</td>
                      <td>{item.tax_group}</td>
                      <td>{item.age_restriction ? 'Yes (18+)' : 'No'}</td>
                      <td>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            setSelectedItem(item);
                            setNewPrice(item.price);
                            setShowModal(true);
                          }}
                        >
                          <FiEdit2 size={12} /> Change Price
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Price Change Requests & Workflow</h2>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Change ID</th>
                    <th>Item Code</th>
                    <th>Variant</th>
                    <th>Old Price</th>
                    <th>New Price</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {priceChanges.map(pc => (
                    <tr key={pc.change_id}>
                      <td style={{ fontWeight: 600 }}>{pc.change_id}</td>
                      <td>{pc.item_code}</td>
                      <td>{pc.variant_code}</td>
                      <td>£{parseFloat(pc.old_price).toFixed(2)}</td>
                      <td style={{ fontWeight: 700, color: 'var(--primary)' }}>£{parseFloat(pc.new_price).toFixed(2)}</td>
                      <td>{pc.reason}</td>
                      <td>
                        <span className={`badge badge-${
                          pc.status === 'Applied' ? 'success' : pc.status === 'Rejected' ? 'danger' : 'pending'
                        }`}>
                          {pc.status}
                        </span>
                      </td>
                      <td>{new Date(pc.created_at).toLocaleString()}</td>
                      <td>
                        {pc.status === 'Pending' && (
                          <div style={{ display: 'flex', gap: '4px' }}>
                            <button className="btn btn-success btn-sm" onClick={() => handleApprove(pc.change_id)}>
                              <FiCheck size={12} /> Approve
                            </button>
                            <button className="btn btn-danger btn-sm" onClick={() => handleReject(pc.change_id)}>
                              <FiX size={12} /> Reject
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Price Change Modal */}
      {showModal && selectedItem && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3 className="modal-title">Request Price Change</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}><FiX size={18} /></button>
            </div>
            <form onSubmit={handleCreatePriceChange}>
              <div className="modal-body">
                <div style={{ marginBottom: '16px', background: 'var(--background)', padding: '12px', borderRadius: 'var(--radius)' }}>
                  <div><strong>Item:</strong> {selectedItem.description} ({selectedItem.item_code})</div>
                  <div><strong>Current Price:</strong> £{parseFloat(selectedItem.price).toFixed(2)}</div>
                </div>

                <div className="form-group">
                  <label className="form-label">New Price (£)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="form-input"
                    value={newPrice}
                    onChange={(e) => setNewPrice(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Reason for Change</label>
                  <input
                    type="text"
                    className="form-input"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="e.g., Supplier price increase, promotional sale"
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Submit Price Change Request</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}