import React, { useState, useEffect } from 'react';
import { reconciliationApi } from '../api/client';
import { FiCheckCircle, FiAlertTriangle, FiDollarSign, FiCalendar, FiFilter } from 'react-icons/fi';

export default function ReconciliationPage({ storeId, dateRange }) {
  const [activeTab, setActiveTab] = useState('shift'); // 'shift', 'eod', 'variance', 'discrepancies'
  const [shiftSummaries, setShiftSummaries] = useState([]);
  const [eodSummaries, setEodSummaries] = useState([]);
  const [varianceReport, setVarianceReport] = useState([]);
  const [discrepancies, setDiscrepancies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [storeId, dateRange, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {
        store_id: storeId,
        start_date: dateRange.start,
        end_date: dateRange.end,
      };

      if (activeTab === 'shift') {
        const res = await reconciliationApi.getShiftSummaries(params);
        setShiftSummaries(res.data);
      } else if (activeTab === 'eod') {
        const res = await reconciliationApi.getEODSummaries(params);
        setEodSummaries(res.data);
      } else if (activeTab === 'variance') {
        const res = await reconciliationApi.getCashVarianceReport(params);
        setVarianceReport(res.data.report || []);
      } else if (activeTab === 'discrepancies') {
        const res = await reconciliationApi.getDiscrepancies({ ...params, threshold: 0.01 });
        setDiscrepancies(res.data.discrepancies || []);
      }
    } catch (err) {
      console.error('Failed to load reconciliation data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
        <TabButton active={activeTab === 'shift'} onClick={() => setActiveTab('shift')}>
          Shift Summaries
        </TabButton>
        <TabButton active={activeTab === 'eod'} onClick={() => setActiveTab('eod')}>
          End of Day Summaries
        </TabButton>
        <TabButton active={activeTab === 'variance'} onClick={() => setActiveTab('variance')}>
          Cash Variance Report
        </TabButton>
        <TabButton active={activeTab === 'discrepancies'} onClick={() => setActiveTab('discrepancies')}>
          Audit Discrepancies
        </TabButton>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner"></div></div>
      ) : (
        <>
          {activeTab === 'shift' && <ShiftSummariesTable summaries={shiftSummaries} />}
          {activeTab === 'eod' && <EODSummariesTable summaries={eodSummaries} />}
          {activeTab === 'variance' && <CashVarianceTable report={varianceReport} />}
          {activeTab === 'discrepancies' && <DiscrepanciesTable list={discrepancies} />}
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

function ShiftSummariesTable({ summaries }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Shift Summaries & Reconciliation</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Date</th>
                <th>Shift</th>
                <th>Store</th>
                <th>Reported Sales</th>
                <th>Calculated Sales</th>
                <th>Opening Float</th>
                <th>Counted Cash</th>
                <th>Expected Cash</th>
                <th>Cash Variance</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map(s => {
                const variance = parseFloat(s.cash_variance);
                const hasVariance = Math.abs(variance) > 0.01;
                return (
                  <tr key={s.id}>
                    <td>{s.date}</td>
                    <td>Shift {s.shift_num}</td>
                    <td>{s.store_name}</td>
                    <td>£{formatCurrency(s.reported_total_sales)}</td>
                    <td>£{formatCurrency(s.calculated_sales)}</td>
                    <td>£{formatCurrency(s.opening_float)}</td>
                    <td>£{formatCurrency(s.counted_cash)}</td>
                    <td>£{formatCurrency(parseFloat(s.counted_cash) - variance)}</td>
                    <td style={{ color: variance < 0 ? 'var(--danger)' : variance > 0 ? 'var(--success)' : 'inherit', fontWeight: 600 }}>
                      {variance > 0 ? '+' : ''}£{formatCurrency(s.cash_variance)}
                    </td>
                    <td>
                      {hasVariance ? (
                        <span className="badge badge-danger" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FiAlertTriangle size={12} /> Variance
                        </span>
                      ) : (
                        <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FiCheckCircle size={12} /> Matched
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EODSummariesTable({ summaries }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">End of Day (EOD) Summaries</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Date</th>
                <th>Store</th>
                <th>Reported Sales</th>
                <th>Calculated Sales</th>
                <th>Sales Var</th>
                <th>Reported Tax</th>
                <th>Calculated Tax</th>
                <th>Tax Var</th>
                <th>Cash Var</th>
                <th>Txn Var</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map(e => (
                <tr key={e.id}>
                  <td>{e.date}</td>
                  <td>{e.store_name}</td>
                  <td>£{formatCurrency(e.reported_total_sales)}</td>
                  <td>£{formatCurrency(e.calculated_total_sales)}</td>
                  <td style={{ color: parseFloat(e.sales_variance) !== 0 ? 'var(--danger)' : 'inherit' }}>
                    £{formatCurrency(e.sales_variance)}
                  </td>
                  <td>£{formatCurrency(e.reported_total_tax)}</td>
                  <td>£{formatCurrency(e.calculated_tax)}</td>
                  <td style={{ color: parseFloat(e.tax_variance) !== 0 ? 'var(--danger)' : 'inherit' }}>
                    £{formatCurrency(e.tax_variance)}
                  </td>
                  <td style={{ color: parseFloat(e.cash_variance) !== 0 ? 'var(--danger)' : 'inherit' }}>
                    £{formatCurrency(e.cash_variance)}
                  </td>
                  <td style={{ color: e.transaction_variance !== 0 ? 'var(--danger)' : 'inherit' }}>
                    {e.transaction_variance}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CashVarianceTable({ report }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Cash Position & Variance Report</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Date</th>
                <th>Store</th>
                <th>Opening Float</th>
                <th>Cash Sales</th>
                <th>Cash Refunds</th>
                <th>Cash Drops</th>
                <th>Expected Cash</th>
                <th>Counted Cash</th>
                <th>Variance</th>
              </tr>
            </thead>
            <tbody>
              {report.map((r, i) => {
                const varNum = parseFloat(r.variance);
                return (
                  <tr key={i}>
                    <td>{r.date}</td>
                    <td>{r.store_name}</td>
                    <td>£{formatCurrency(r.opening_float)}</td>
                    <td>£{formatCurrency(r.cash_sales)}</td>
                    <td>£{formatCurrency(r.cash_refunds)}</td>
                    <td>£{formatCurrency(r.cash_drops)}</td>
                    <td style={{ fontWeight: 600 }}>£{formatCurrency(r.expected_cash)}</td>
                    <td style={{ fontWeight: 600 }}>£{formatCurrency(r.counted_cash)}</td>
                    <td style={{
                      fontWeight: 700,
                      color: varNum < 0 ? 'var(--danger)' : varNum > 0 ? 'var(--success)' : 'inherit'
                    }}>
                      {varNum > 0 ? '+' : ''}£{formatCurrency(r.variance)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DiscrepanciesTable({ list }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Audit Discrepancies (Over Threshold)</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Date</th>
                <th>Store</th>
                <th>Field</th>
                <th>Reported / Counted</th>
                <th>Calculated</th>
                <th>Variance</th>
              </tr>
            </thead>
            <tbody>
              {list.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>
                    No discrepancies found above threshold
                  </td>
                </tr>
              ) : (
                list.map((d, i) => (
                  <tr key={i}>
                    <td>{d.date}</td>
                    <td>{d.store_name}</td>
                    <td style={{ textTransform: 'capitalize' }}>{d.field.replace('_', ' ')}</td>
                    <td>£{formatCurrency(d.reported)}</td>
                    <td>{d.calculated === 'N/A' ? 'N/A' : `£${formatCurrency(d.calculated)}`}</td>
                    <td style={{ color: 'var(--danger)', fontWeight: 600 }}>£{formatCurrency(d.variance)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function formatCurrency(val) {
  if (val === null || val === undefined) return '0.00';
  return parseFloat(val).toFixed(2);
}