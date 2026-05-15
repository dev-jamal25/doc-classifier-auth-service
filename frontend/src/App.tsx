import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./lib/auth";
import { BatchDetailPage } from "./pages/BatchDetailPage";
import { BatchesPage } from "./pages/BatchesPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DemoIngestionPage } from "./pages/DemoIngestionPage";
import { LoginPage } from "./pages/LoginPage";
import { ReviewPage } from "./pages/ReviewPage";

function RootRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? "/dashboard" : "/login"} replace />;
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}

export function App() {
  return (
    <Routes>
      <Route element={<RootRedirect />} path="/" />
      <Route element={<LoginPage />} path="/login" />
      <Route
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
        path="/dashboard"
      />
      <Route
        element={
          <ProtectedRoute>
            <BatchesPage />
          </ProtectedRoute>
        }
        path="/batches"
      />
      <Route
        element={
          <ProtectedRoute>
            <BatchDetailPage />
          </ProtectedRoute>
        }
        path="/batches/:batchId"
      />
      <Route
        element={
          <ProtectedRoute>
            <ReviewPage />
          </ProtectedRoute>
        }
        path="/predictions/review"
      />
      <Route
        element={
          <ProtectedRoute>
            <DemoIngestionPage />
          </ProtectedRoute>
        }
        path="/demo-ingestion"
      />
      <Route element={<Navigate to="/" replace />} path="*" />
    </Routes>
  );
}
