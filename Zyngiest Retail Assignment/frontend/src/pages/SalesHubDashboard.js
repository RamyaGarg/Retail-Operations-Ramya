import React, { useState, useEffect, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
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
import {
  FiTrendingUp,
  FiDollarSign,
  FiShoppingCart,
  FiPercent,
  FiBarChart2,
  FiTarget,
  FiUsers,
  FiActivity,
  FiAward,
  FiAlertTriangle,
  FiCheckCircle,
  FiCalendar,
  FiFilter,
  FiDownload,
  FiRefreshCw,
  FiUserPlus,
} from 'react-icons/fi';

const COLORS = ['#1a5f7a', '#2e8b7a', '#d4a52a', '#8e44ad', '#e74c3c', '#3498db', '#27ae60', '#f39c12'];
const CHART_COLORS = ['#1a5f7a', '#2e8b7a', '#d4a52a', '#8e44ad', '#e74c3c'];

/* ===== Reusable Components ===== */

function KpiCard({ icon, label, value, change, changePositive, color }) {
  return (
    <div className="kpi-card" style={{ borderLeft: `4px solid ${color}`, position: 'relative', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <span className="kpi-label">{label}</span>
        <span style={{ color, display: 'flex', alignItems: 'center', background: `${color}15`, padding: '8px', borderRadius: 'var(--radius)' }}>{icon}</span>
      </div>
      <div className="kpi-value" style={{ fontSize: '26px' }}>{value}</div>
      {change && (
        <div className="kpi-change" style={{ marginTop: '8px' }}>
          <span className={changePositive ? 'positive' : 'negative'} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {changePositive ? <FiTrendingUp size={14} /> : <FiActivity size={14} />}
            {change}
          </span>
        </div>
      )}
    </div>
  );
}

function MetricBox({ label, value, icon, color }) {
  return (
    <div style={{ padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ color, display: 'flex', background: `${color}15`, padding: '6px', borderRadius: '6px' }}>{icon}</span>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</span>
      </div>
      <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}

function HealthBar({ label, value, target, color, invert = false }) {
  const displayValue = invert ? 100 - value : value;
  const isGood = invert ? value <= target : value >= target;
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontSize: '13px', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: '13px', fontWeight: 600, color: isGood ? 'var(--success)' : 'var(--danger)' }}>
          {displayValue.toFixed(0)}% {isGood ? 'OK' : 'WARN'}
        </span>
      </div>
      <div style={{ height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{
          width: `${Math.min(Math.max(displayValue, 0), 100)}%`,
          height: '100%',
          background: isGood ? color : 'var(--danger)',
          borderRadius: '3px',
          transition: 'width 0.3s ease'
        }}></div>
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', textAlign: 'right' }}>
        Target: {target}%
      </div>
    </div>
  );
}

function SalesTrendChart({ data, forecast }) {
  const combinedData = useMemo(() => {
    if (!data.length) return [];
    const lastDate = new Date(data[data.length - 1].date);
    const forecastPoints = forecast.filter(f => new Date(f.date) > lastDate).slice(0, 7);
    return [...data, ...forecastPoints.map(f => ({
      date: f.date,
      sales: parseFloat(f.predicted_sales),
      isForecast: true
    }))];
  }, [data, forecast]);

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Sales Trend</h2>
        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Last 30 days + 7-day forecast</span>
      </div>
      <div className="card-body">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={combinedData}>
            <defs>
              <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1a5f7a" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#1a5f7a" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8e44ad" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#8e44ad" stopOpacity={0.05}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={(val) => new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(val) => `£${formatNumber(val)}`}
            />
            <Tooltip
              formatter={(value, name) => [`£${formatCurrency(value)}`, name === 'sales' ? 'Actual' : 'Forecast']}
              labelFormatter={(label) => new Date(label).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short' })}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="sales"
              stroke="#1a5f7a"
              fill="url(#salesGrad)"
              strokeWidth={2}
              name="Actual"
            />
            <Area
              type="monotone"
              dataKey="sales"
              stroke="#8e44ad"
              fill="url(#forecastGrad)"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Forecast"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TenderMixChart({ data }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Payment Methods</h2>
      </div>
      <div className="card-body">
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data.map(t => ({ name: t.type, value: parseFloat(t.amount) }))}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={4}
              dataKey="value"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => [`£${formatCurrency(value)}`, 'Amount']} />
            <Legend layout="vertical" align="right" verticalAlign="middle" />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TopItemsTable({ items }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Top Selling Items</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th style={{ width: '50%' }}>Item</th>
                <th>Qty</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 8).map((item, idx) => (
                <tr key={item.item_code}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        background: COLORS[idx % COLORS.length], color: 'white',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '11px', fontWeight: 600
                      }}>
                        {idx + 1}
                      </span>
                      <div>
                        <div style={{ fontWeight: 500, fontSize: '13px' }}>{item.description}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{item.item_code}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 500 }}>{formatNumber(item.quantity_sold)}</td>
                  <td style={{ fontWeight: 500 }}>£{formatCurrency(item.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function DepartmentPerformanceChart({ data }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Department Performance</h2>
      </div>
      <div className="card-body">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(val) => `£${formatNumber(val)}`} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(val) => `${val}%`} />
            <Tooltip
              formatter={(value, name) => {
                if (name === 'margin_pct') return [`${value}%`, 'Margin'];
                return [`£${formatCurrency(value)}`, name];
              }}
            />
            <Legend />
            <Bar yAxisId="left" dataKey="revenue" name="Revenue" fill="#1a5f7a" barSize={25} radius={[4, 4, 0, 0]} />
            <Bar yAxisId="left" dataKey="cost" name="Cost" fill="#e74c3c" barSize={25} radius={[4, 4, 0, 0]} />
            <Line yAxisId="right" type="monotone" dataKey="margin_pct" name="Margin %" stroke="#d4a52a" strokeWidth={2} dot={{ r: 4 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PeriodComparisonCard({ data, mode }) {
  if (!data) return null;
  const curr = data.current_period;
  const prior = data.prior_period;
  const salesChange = parseFloat(data.variance_pct);
  const txnChange = ((curr.transactions - prior.transactions) / prior.transactions * 100) || 0;

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Period Comparison</h2>
        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          {mode === 'prior_year' ? 'Year-over-Year' : 'Period-over-Period'}
        </span>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <ComparisonMetric
            label="Sales"
            current={`£${formatCurrency(curr.sales)}`}
            prior={`£${formatCurrency(prior.sales)}`}
            change={data.variance_pct}
            positive={salesChange >= 0}
          />
          <ComparisonMetric
            label="Transactions"
            current={formatNumber(curr.transactions)}
            prior={formatNumber(prior.transactions)}
            change={txnChange.toFixed(1)}
            positive={txnChange >= 0}
          />
          <ComparisonMetric
            label="Avg Ticket"
            current={`£${formatCurrency(curr.avg_ticket)}`}
            prior={`£${formatCurrency(prior.avg_ticket)}`}
            change={(((parseFloat(curr.avg_ticket) - parseFloat(prior.avg_ticket)) / parseFloat(prior.avg_ticket) * 100) || 0).toFixed(1)}
            positive={parseFloat(curr.avg_ticket) >= parseFloat(prior.avg_ticket)}
          />
          <ComparisonMetric
            label="Tax"
            current={`£${formatCurrency(curr.tax)}`}
            prior={`£${formatCurrency(prior.tax)}`}
            change={(((parseFloat(curr.tax) - parseFloat(prior.tax)) / parseFloat(prior.tax) * 100) || 0).toFixed(1)}
            positive={parseFloat(curr.tax) >= parseFloat(prior.tax)}
          />
        </div>
      </div>
    </div>
  );
}

function ComparisonMetric({ label, current, prior, change, positive }) {
  return (
    <div style={{ padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ fontSize: '22px', fontWeight: '700', marginBottom: '4px' }}>{current}</div>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
        vs {prior}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: positive ? 'var(--success)' : 'var(--danger)', fontWeight: 600, fontSize: '13px' }}>
        {positive ? <FiTrendingUp size={14} /> : <FiActivity size={14} />}
        {change > 0 ? '+' : ''}{change}%
      </div>
    </div>
  );
}

function PromotionsSummaryCard({ data }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Active Promotions</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Promotion</th>
                <th>Period</th>
                <th>Uplift</th>
              </tr>
            </thead>
            <tbody>
              {data.map(p => (
                <tr key={p.promotion_id}>
                  <td style={{ fontWeight: 500 }}>{p.name}</td>
                  <td style={{ fontSize: '12px' }}>{p.start_date} – {p.end_date}</td>
                  <td style={{ color: parseFloat(p.uplift_pct) >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                    {parseFloat(p.uplift_pct) > 0 ? '+' : ''}{p.uplift_pct}%
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>No active promotions</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TargetsSummaryCard({ data }) {
  const avgAttainment = data.length > 0 ? data.reduce((sum, t) => sum + parseFloat(t.attainment_pct), 0) / data.length : 0;
  const achieved = data.filter(t => parseFloat(t.attainment_pct) >= 100).length;

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Quota Summary</h2>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
          <div style={{ textAlign: 'center', padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
            <div style={{ fontSize: '36px', fontWeight: '700', color: avgAttainment >= 100 ? 'var(--success)' : avgAttainment >= 80 ? 'var(--warning)' : 'var(--danger)' }}>
              {avgAttainment.toFixed(1)}%
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Avg Attainment</div>
          </div>
          <div style={{ textAlign: 'center', padding: '16px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
            <div style={{ fontSize: '36px', fontWeight: '700', color: 'var(--primary)' }}>
              {achieved}/{data.length}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Stores at Target</div>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {data.slice(0, 3).map(t => (
            <div key={t.target_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--background)', borderRadius: 'var(--radius)' }}>
              <span style={{ fontWeight: 500, fontSize: '13px' }}>{t.store_name}</span>
              <span style={{ fontWeight: 600, color: parseFloat(t.attainment_pct) >= 100 ? 'var(--success)' : parseFloat(t.attainment_pct) >= 80 ? 'var(--warning)' : 'var(--danger)' }}>
                {t.attainment_pct}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StaffSummaryCard({ data }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Top Performers</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="table-container">
          <table className="reconciliation">
            <thead>
              <tr>
                <th>Staff</th>
                <th>Sales</th>
                <th>Sales/Hr</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s, idx) => (
                <tr key={s.staff_id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        width: '24px', height: '24px', borderRadius: '50%',
                        background: CHART_COLORS[idx % CHART_COLORS.length], color: 'white',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '11px', fontWeight: 600
                      }}>
                        {idx + 1}
                      </span>
                      <span style={{ fontWeight: 500, fontSize: '13px' }}>{s.name}</span>
                    </div>
                  </td>
                  <td>£{formatCurrency(s.total_sales)}</td>
                  <td style={{ fontWeight: 600, color: 'var(--primary)' }}>£{formatCurrency(s.sales_per_hour)}</td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>No data</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ===== Tab Components ===== */

function OverviewTab({ executiveScorecard, salesTrend, forecast, tenderMix, topItems, deptPerf, periodComparison, compareMode, promotions, targets }) {
  return (
    <>
      {/* Executive Scorecard Alerts */}
      {executiveScorecard?.alerts?.length > 0 && (
        <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid var(--warning)' }}>
          <div className="card-body" style={{ padding: '16px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <FiAlertTriangle size={20} style={{ color: 'var(--warning)', marginTop: '2px', flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, marginBottom: '8px' }}>Executive Alerts</div>
                <ul style={{ margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)' }}>
                  {executiveScorecard.alerts.map((alert, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>{alert}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Charts Row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <SalesTrendChart data={salesTrend} forecast={forecast} />
        <TenderMixChart data={tenderMix} />
      </div>

      {/* Charts Row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <TopItemsTable items={topItems} />
        <DepartmentPerformanceChart data={deptPerf} />
      </div>

      {/* Bottom Row - Period Comparison + Promotions + Targets Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
        <PeriodComparisonCard data={periodComparison} mode={compareMode} />
        <PromotionsSummaryCard data={promotions.slice(0, 3)} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <TargetsSummaryCard data={targets} />
        <div className="card">
          <div className="card-body" style={{ padding: '16px 24px' }}>
            <div style={{ fontWeight: 600, marginBottom: '12px', color: 'var(--text-primary)' }}>Quick Actions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <button className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                <FiDownload size={16} style={{ marginRight: '8px' }} />
                Export Report
              </button>
              <button className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                <FiFilter size={16} style={{ marginRight: '8px' }} />
                Advanced Filters
              </button>
              <button className="btn btn-secondary btn-sm" style={{ justifyContent: 'flex-start' }}>
                <FiRefreshCw size={16} style={{ marginRight: '8px' }} />
                Refresh Data
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function TargetsTab({ targets, periodComparison, compareMode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <TargetsSummaryCard data={targets} />
      <PeriodComparisonCard data={periodComparison} mode={compareMode} />
    </div>
  );
}

function PromotionsTab({ promotions }) {
  return (
    <div className="card">
      <div className="card-body">
        <PromotionsSummaryCard data={promotions} />
      </div>
    </div>
  );
}

function StaffTab({ staffPerformance }) {
  return (
    <div className="card">
      <div className="card-body">
        <StaffSummaryCard data={staffPerformance} />
      </div>
    </div>
  );
}

function ForecastTab({ forecast }) {
  const forecastData = forecast || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Sales Forecast</h2>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>7-day prediction</span>
        </div>
        <div className="card-body">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={forecastData}>
              <defs>
                <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8e44ad" stopOpacity={0.5}/>
                  <stop offset="95%" stopColor="#8e44ad" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickFormatter={(val) => new Date(val).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(val) => `£${formatNumber(val)}`}
              />
              <Tooltip
                formatter={(value) => [`£${formatCurrency(value)}`, 'Forecast']}
                labelFormatter={(label) => new Date(label).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short' })}
              />
              <Bar
                dataKey="predicted_sales"
                fill="url(#forecastGrad)"
                stroke="#8e44ad"
                strokeWidth={1}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function CustomersTab({ customerMetrics }) {
  if (!customerMetrics) {
    return (
      <div className="card">
        <div className="card-body" style={{ padding: '24px', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading customer data...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Customer Metrics</h2>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Customer Health Overview</span>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px' }}>
            <MetricBox
              label="Total Customers"
              value={customerMetrics.total_customers}
              icon={<FiUsers size={24} />}
              color="#3498db"
            />
            <MetricBox
              label="New Customers"
              value={customerMetrics.new_customers}
              icon={<FiUserPlus size={24} />}
              color="#1a5f7a"
            />
            <MetricBox
              label="Returning Rate"
              value={`${Math.round(customerMetrics.returning_customers / customerMetrics.total_customers * 100)}%`}
              icon={<FiRefreshCw size={24} />}
              color="#2e8b7a"
            />
            <MetricBox
              label="Avg Frequency"
              value={customerMetrics.avg_frequency}
              icon={<FiBarChart2 size={24} />}
              color="#d4a52a"
            />
            <MetricBox
              label="Avg Recency"
              value={`${customerMetrics.avg_recency_days} days`}
              icon={<FiCalendar size={24} />}
              color="#8e44ad"
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Customer Health Indicators</h2>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            <MetricBox
              label="New Customer Rate"
              value={`${Math.round(customerMetrics.new_customers / customerMetrics.total_customers * 100)}%`}
              icon={<FiBarChart2 size={24} />}
              color="#2e8b7a"
            />
            <MetricBox
              label="Return Rate"
              value={`${Math.round(customerMetrics.returning_customers / customerMetrics.total_customers * 100)}%`}
              icon={<FiActivity size={24} />}
              color="#1a5f7a"
            />
            <MetricBox
              label="Frequency Score"
              value={customerMetrics.avg_frequency}
              icon={<FiAward size={24} />}
              color="#d4a52a"
            />
            <MetricBox
              label="Recency Score"
              value={customerMetrics.avg_recency_days}
              icon={<FiTrendingUp size={24} />}
              color="#8e44ad"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function formatCurrency(value) {
  if (value === null || value === undefined) return '0.00';
  return parseFloat(value).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber(value) {
  if (value === null || value === undefined) return '0';
  return parseFloat(value).toLocaleString('en-GB');
}

/* ===== Main Dashboard Component ===== */

export default function SalesHubDashboard({ storeId, dateRange, onDateRangeChange }) {
  // Core dashboard state
  const [kpis, setKpis] = useState(null);
  const [salesTrend, setSalesTrend] = useState([]);
  const [topItems, setTopItems] = useState([]);
  const [tenderMix, setTenderMix] = useState([]);
  const [deptPerf, setDeptPerf] = useState([]);

  // Sales Hub features state
  const [targets, setTargets] = useState([]);
  const [periodComparison, setPeriodComparison] = useState(null);
  const [promotions, setPromotions] = useState([]);
  const [staffPerformance, setStaffPerformance] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [customerMetrics, setCustomerMetrics] = useState(null);
  const [executiveScorecard, setExecutiveScorecard] = useState(null);

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // overview, targets, promotions, staff, forecast, customers
  const [compareMode, setCompareMode] = useState('prior_period');

  useEffect(() => {
    loadAllData();
  }, [storeId, dateRange, compareMode, activeTab]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const params = {
        store_id: storeId,
        start_date: dateRange.start,
        end_date: dateRange.end,
      };

      // Core dashboard (always load)
      const [kpiRes, trendRes, topRes, tenderRes, deptRes] = await Promise.all([
        dashboardApi.getKPIs(params),
        dashboardApi.getSalesTrend({ store_id: storeId, days: 30 }),
        dashboardApi.getTopItems({ store_id: storeId, start_date: dateRange.start, end_date: dateRange.end }),
        dashboardApi.getTenderMix(params),
        dashboardApi.getDepartmentPerformance(params),
      ]);

      setKpis(kpiRes.data);
      setSalesTrend(trendRes.data);
      setTopItems(topRes.data);
      setTenderMix(tenderRes.data.tender_mix || []);
      setDeptPerf(deptRes.data.departments || []);

      // Sales Hub features based on active tab
      const hubPromises = [];
      if (activeTab === 'overview' || activeTab === 'targets') {
        hubPromises.push(dashboardApi.getSalesTargets(params).then(setTargets));
        hubPromises.push(dashboardApi.getPeriodComparison({ ...params, compare_to: compareMode }).then(setPeriodComparison));
      }
      if (activeTab === 'overview' || activeTab === 'promotions') {
        hubPromises.push(dashboardApi.getPromotions(params).then(setPromotions));
      }
      if (activeTab === 'overview' || activeTab === 'staff') {
        hubPromises.push(dashboardApi.getStaffPerformance(params).then(setStaffPerformance));
      }
      if (activeTab === 'overview' || activeTab === 'forecast') {
        hubPromises.push(dashboardApi.getForecast({ store_id: storeId }).then(setForecast));
      }
      if (activeTab === 'overview' || activeTab === 'customers') {
        hubPromises.push(dashboardApi.getCustomerMetrics(params).then(setCustomerMetrics));
      }
      if (activeTab === 'overview') {
        hubPromises.push(dashboardApi.getExecutiveScorecard(params).then(setExecutiveScorecard));
      }

      await Promise.all(hubPromises);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const periodLabel = useMemo(() => {
    const start = new Date(dateRange.start);
    const end = new Date(dateRange.end);
    return `${start.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })} – ${end.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}`;
  }, [dateRange]);

  if (loading) {
    return (
      <div className="loading" style={{ padding: '60px' }}>
        <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0 24px 24px' }}>
      {/* Header with controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>Sales Hub</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Microsoft Dynamics 365-style retail analytics</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <select
            value={activeTab}
            onChange={(e) => setActiveTab(e.target.value)}
            className="form-select"
            style={{ minWidth: '160px', padding: '8px 36px 8px 12px' }}
          >
            <option value="overview">Overview</option>
            <option value="targets">Quota & Targets</option>
            <option value="promotions">Promotions</option>
            <option value="staff">Staff Performance</option>
            <option value="forecast">Forecasting</option>
            <option value="customers">Customer Insights</option>
          </select>
          {activeTab === 'targets' && (
            <select
              value={compareMode}
              onChange={(e) => setCompareMode(e.target.value)}
              className="form-select"
              style={{ minWidth: '160px', padding: '8px 36px 8px 12px' }}
            >
              <option value="prior_period">Prior Period</option>
              <option value="prior_year">Prior Year (YoY)</option>
            </select>
          )}
          <button className="btn btn-secondary btn-sm" onClick={loadAllData} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FiRefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {/* KPI Row - always visible */}
      <div className="kpi-grid" style={{ marginBottom: '24px' }}>
        <KpiCard
          icon={<FiDollarSign size={24} />}
          label="Total Sales"
          value={kpis ? `£${formatCurrency(kpis.total_sales)}` : '—'}
          change={executiveScorecard?.revenue?.variance_pct ? `${parseFloat(executiveScorecard.revenue.variance_pct) > 0 ? '+' : ''}${executiveScorecard.revenue.variance_pct}%` : null}
          changePositive={executiveScorecard?.revenue?.variance_pct ? parseFloat(executiveScorecard.revenue.variance_pct) >= 0 : true}
          color="#1a5f7a"
        />
        <KpiCard
          icon={<FiShoppingCart size={24} />}
          label="Transactions"
          value={kpis ? formatNumber(kpis.total_transactions) : '—'}
          change={executiveScorecard?.transactions?.variance_pct ? `${parseFloat(executiveScorecard.transactions.variance_pct) > 0 ? '+' : ''}${executiveScorecard.transactions.variance_pct}%` : null}
          changePositive={executiveScorecard?.transactions?.variance_pct ? parseFloat(executiveScorecard.transactions.variance_pct) >= 0 : true}
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
          value={executiveScorecard?.margin ? `£${formatCurrency(executiveScorecard.margin.gross_margin)} (${executiveScorecard.margin.margin_pct}%)` : (kpis ? `£${formatCurrency(kpis.gross_margin)}` : '—')}
          color="#8e44ad"
        />
        <KpiCard
          icon={<FiTarget size={24} />}
          label="Quota Attainment"
          value={targets.length > 0 ? `${targets.reduce((sum, t) => sum + parseFloat(t.attainment_pct), 0) / targets.length}%` : '—'}
          color="#e74c3c"
        />
        <KpiCard
          icon={<FiUsers size={24} />}
          label="Active Customers"
          value={customerMetrics ? customerMetrics.total_customers : '—'}
          change={customerMetrics ? `+${customerMetrics.new_customers} new` : null}
          changePositive={true}
          color="#3498db"
        />
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab
          executiveScorecard={executiveScorecard}
          salesTrend={salesTrend}
          forecast={forecast}
          tenderMix={tenderMix}
          topItems={topItems}
          deptPerf={deptPerf}
          periodComparison={periodComparison}
          compareMode={compareMode}
          promotions={promotions}
          targets={targets}
        />
      )}
      {activeTab === 'targets' && (
        <TargetsTab
          targets={targets}
          periodComparison={periodComparison}
          compareMode={compareMode}
        />
      )}
      {activeTab === 'promotions' && (
        <PromotionsTab promotions={promotions} />
      )}
      {activeTab === 'staff' && (
        <StaffTab staffPerformance={staffPerformance} />
      )}
      {activeTab === 'forecast' && (
        <ForecastTab forecast={forecast} />
      )}
      {activeTab === 'customers' && (
        <CustomersTab customerMetrics={customerMetrics} />
      )}
    </div>
  );
}