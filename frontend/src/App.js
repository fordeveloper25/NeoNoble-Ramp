import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Web3Provider } from "./context/Web3Context";
import { Toaster } from "@/components/ui/sonner";
import { NotificationToaster } from "./components/NotificationSystem";
import { WalletModal } from "./components/WalletConnect";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import DevPortal from "./pages/DevPortal";
import DevLogin from "./pages/DevLogin";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import AdminDashboard from "./pages/AdminDashboard";
import TokenCreation from "./pages/TokenCreation";
import TokenList from "./pages/TokenList";
import SubscriptionPlans from "./pages/SubscriptionPlans";

// Protected Route Component
function ProtectedRoute({ children, requireDeveloper = false }) {
  const { isAuthenticated, isDeveloper, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireDeveloper && !isDeveloper) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

// Public Route (redirect if logged in)
function PublicRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      
      <Route
        path="/signup"
        element={
          <PublicRoute>
            <Signup />
          </PublicRoute>
        }
      />
      
      <Route
        path="/forgot-password"
        element={
          <PublicRoute>
            <ForgotPassword />
          </PublicRoute>
        }
      />
      
      <Route
        path="/reset-password"
        element={<ResetPassword />}
      />
      
      <Route
        path="/dev/login"
        element={
          <PublicRoute>
            <DevLogin />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      {/* Developer Portal (requires developer role) */}
      <Route
        path="/dev"
        element={
          <ProtectedRoute requireDeveloper>
            <DevPortal />
          </ProtectedRoute>
        }
      />

      {/* Admin Dashboard */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />

      {/* Token Routes */}
      <Route
        path="/tokens/create"
        element={
          <ProtectedRoute>
            <TokenCreation />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tokens/list"
        element={
          <ProtectedRoute>
            <TokenList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tokens"
        element={<Navigate to="/tokens/list" replace />}
      />

      {/* Subscription Routes */}
      <Route
        path="/subscriptions"
        element={
          <ProtectedRoute>
            <SubscriptionPlans />
          </ProtectedRoute>
        }
      />

      {/* Catch all - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Web3Provider>
          <AuthProvider>
            <AppRoutes />
            <Toaster />
            <NotificationToaster />
            <WalletModal />
          </AuthProvider>
        </Web3Provider>
      </BrowserRouter>
    </div>
  );
}

export default App;
