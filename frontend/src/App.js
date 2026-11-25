import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { dashboardApi } from './api/client';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardPage from './pages/DashboardPage';
import ReconciliationPage from './pages/ReconciliationPage';
import PricingPage from './pages/PricingPage';
import ConnectorsPage from './pages/ConnectorsPage';
import AIPage from './pages/AIPage';
import HubPage from './pages/HubPage';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentStore, setCurrentStore] = useState(1);
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });
  const [stores, setStores] = useState([]);
  const [hubStatus, setHubStatus] = useState({ running: false });

  // Load stores on mount
  useEffect(() => {
    dashboardApi.getStoreComparison().then(res => {
      setStores(res.data.stores || []);
    }).catch(() => {
      // Fallback stores
      setStores([
        { store_id: 1, name: 'Brightleaf Downtown', location: '123 Main St' },
        { store_id: 2, name: 'Brightleaf Mall', location: '456 Oak Ave' },
      ]);
    });
  }, []);

  // Poll hub status
  useEffect(() => {
    const checkHub = async () => {
      try {
        const res = await fetch('/api/hub/status');
        const data = await res.json();
        setHubStatus(data);
      } catch (e) {
        // ignore
      }
    };
    checkHub();
    const interval = setInterval(checkHub, 10000);
    return () => clearInterval(interval);
  }, []);

  const currentStoreObj = stores.find(s => s.store_id === currentStore) || stores[0];

  return (
    <Router>
      <div className="app-layout">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          currentStore={currentStore}
          stores={stores}
          onStoreChange={setCurrentStore}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
          hubStatus={hubStatus}
        />

        <div className="main-content">
          <Header
            pageTitle={getPageTitle()}
            currentStore={currentStoreObj}
            onMenuClick={() => setSidebarOpen(true)}
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
          />

          <main className="content">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage storeId={currentStore} dateRange={dateRange} />} />
              <Route path="/reconciliation" element={<ReconciliationPage storeId={currentStore} dateRange={dateRange} />} />
              <Route path="/pricing" element={<PricingPage storeId={currentStore} dateRange={dateRange} />} />
              <Route path="/connectors" element={<ConnectorsPage />} />
              <Route path="/ai" element={<AIPage />} />
              <Route path="/hub" element={<HubPage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>
        </div>

        {sidebarOpen && (
          <div
            className="modal-overlay"
            onClick={() => setSidebarOpen(false)}
            style={{ display: window.innerWidth <= 1024 ? 'flex' : 'none' }}
          >
            <div className="modal" style={{ maxWidth: '280px', height: '100vh', borderRadius: 0 }} onClick={e => e.stopPropagation()}>
              <Sidebar
                isOpen={true}
                onClose={() => setSidebarOpen(false)}
                currentStore={currentStore}
                stores={stores}
                onStoreChange={setCurrentStore}
                dateRange={dateRange}
                onDateRangeChange={setDateRange}
                hubStatus={hubStatus}
              />
            </div>
          </div>
        )}
      </div>
    </Router>
  );
}

function getPageTitle() {
  // This would be determined by current route
  return 'Dashboard';
}

export default App;