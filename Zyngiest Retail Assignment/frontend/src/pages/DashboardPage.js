import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ComposedChart,
} from 'recharts';
import { dashboardApi } from '../api/client';
import { FiTrendingUp, FiDollarSign, FiShoppingCart, FiPercent, FiBarChart2 } from 'react-icons/fi';

const COLORS = ['#1a5f7a', '#2e8b7a', '#d4a52a', '#8e44ad', '#e74c3c', '#3498db', '#27ae60', '#f39c12'];

export default function DashboardPage({ storeId, dateRange }) {
  const [kpis, setKpis] = useState(null);
  const [salesTrend, setSalesTrend] = useState([]);
  const [topItems, setTopItems] = useState([]);
  const [departmentPerf, setDepartmentPerf] = useState([]);
  const [tenderMix, setTenderMix] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [storeId, dateRange]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = {
        store_id: storeId,
        start_date: dateRange.start,
        end_date: dateRange.end,
      };

      const [kpiRes, trendRes, topRes, deptRes, tenderRes] = await Promise.all([
        dashboardApi.getKPIs(params),
        dashboardApi.getSalesTrend({ store_id: storeId, days: 30 }),
        dashboardApi.getTopItems({ store_id: storeId, start_date: dateRange.start, end_date: dateRange.end }),
        dashboardApi.getDepartmentPerformance(params),
        dashboardApi.getTenderMix(params),
      ]);

      setKpis(kpiRes.data);
      setSalesTrend(trendRes.data);
      setTopItems(topRes.data);
      setDepartmentPerf(deptRes.data.departments || []);
      setTenderMix(tenderRes.data.tender_mix || []);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          icon={<FiDollarSign size={24} />}
          label="Total Sales"
          value={kpis ? `£${formatCurrency(kpis.total_sales)}` : '—'}
          color="#1a5f7a"
        />
        <KpiCard
          icon={<FiShoppingCart size={24} />}
          label="Transactions"
          value={kpis ? formatNumber(kpis.total_transactions) : '—'}
          color="#2e8b7a"
        />
        <KpiCard
          icon={<FiTrendingUp size={24} />}
          label="Avg. Transaction"
          value={kpis ? `£${formatCurrency(kpis.avg_transaction_value)}` : '—'}
          color="#d4a52a"
        />
        <KpiCard
          icon={<FiPercent size={24} />}
          label="Gross Margin"
          value={kpis ? `£${formatCurrency(kpis.gross_margin)}` : '—'}
          color="#8e44ad"
        />
        <KpiCard
          icon={<FiBarChart2 size={24} />}
          label="Total Tax"
          value={kpis ? `£${formatCurrency(kpis.total_tax)}` : '—'}
          color="#3498db"
        />
      </div>

      {/* Sales Trend */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h2 className="card-title">Sales Trend</h2>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Last 30 days</span>
        </div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={salesTrend}>
              <defs>
                <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1a5f7a" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#1a5f7a" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => `£${formatNumber(val)}`}
              />
              <Tooltip
                formatter={(value) => [`£${formatCurrency(value)}`, 'Sales']}
                labelFormatter={(label) => new Date(label).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short' })}
              />
              <Area
                type="monotone"
                dataKey="sales"
                stroke="#1a5f7a"
                fill="url(#salesGrad)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        {/* Top Items */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Top Items</h2>
          </div>
          <div className="card-body" style={{ padding: '0' }}>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Qty Sold</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {topItems.map((item, idx) => (
                    <tr key={item.item_code}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '50%',
                            background: COLORS[idx % COLORS.length],
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '11px',
                            fontWeight: 600,
                          }}>
                            {idx + 1}
                          </span>
                          <div>
                            <div style={{ fontWeight: 500 }}>{item.description}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{item.item_code}</div>
                          </div>
                        </div>
                      </td>
                      <td>{formatNumber(item.quantity_sold)}</td>
                      <td>£{formatCurrency(item.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Tender Mix */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Payment Methods</h2>
          </div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={tenderMix.map(t => ({ name: t.type, value: parseFloat(t.amount) }))}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {tenderMix.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [`£${formatCurrency(value)}`, 'Amount']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Department Performance */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Department Performance</h2>
        </div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={departmentPerf}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 12 }} tickFormatter={(val) => `£${formatNumber(val)}`} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} tickFormatter={(val) => `${val}%`} />
              <Tooltip formatter={(value) => `£${formatCurrency(value)}`} />
              <Legend />
              <Bar yAxisId="left" dataKey="revenue" name="Revenue" fill="#1a5f7a" barSize={30} />
              <Bar yAxisId="left" dataKey="cost" name="Cost" fill="#e74c3c" barSize={30} />
              <Line yAxisId="right" type="monotone" dataKey="margin_pct" name="Margin %" stroke="#d4a52a" strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ icon, label, value, color }) {
  return (
    <div className="kpi-card">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span className="kpi-label">{label}</span>
        <span style={{ color, display: 'flex', alignItems: 'center' }}>{icon}</span>
      </div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}

function formatCurrency(value) {
  return parseFloat(value).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber(value) {
  return parseFloat(value).toLocaleString('en-GB');
}