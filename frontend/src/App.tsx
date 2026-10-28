import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { AdminRoute, ProtectedRoute } from './components/layout/Guards';
import { Toaster } from './components/ui/Toaster';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import ProfitDashboard from './pages/ProfitDashboard';
import LiveMarket from './pages/LiveMarket';
import Arbitrage from './pages/Arbitrage';
import Strategies from './pages/Strategies';
import Backtester from './pages/Backtester';
import OrderBook from './pages/OrderBook';
import Portfolio from './pages/Portfolio';
import TradeHistory from './pages/TradeHistory';
import RiskSettings from './pages/RiskSettings';
import Profile from './pages/Profile';
import AdminUsers from './pages/admin/Users';
import AdminMetrics from './pages/admin/Metrics';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="profit" element={<ProfitDashboard />} />
          <Route path="market" element={<LiveMarket />} />
          <Route path="arbitrage" element={<Arbitrage />} />
          <Route path="strategies" element={<Strategies />} />
          <Route path="backtester" element={<Backtester />} />
          <Route path="orderbook" element={<OrderBook />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="history" element={<TradeHistory />} />
          <Route path="risk" element={<RiskSettings />} />
          <Route path="profile" element={<Profile />} />
          <Route
            path="admin/users"
            element={
              <AdminRoute>
                <AdminUsers />
              </AdminRoute>
            }
          />
          <Route
            path="admin/metrics"
            element={
              <AdminRoute>
                <AdminMetrics />
              </AdminRoute>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
