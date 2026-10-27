import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import { AnalysisProvider } from './contexts/AnalysisContext'
import { AppLayout } from './components/layout/AppLayout'
import { ProtectedRoute, PublicRoute } from './components/ProtectedRoute'

// Pages
import { WelcomePage } from './pages/WelcomePage'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { IngestionPage } from './pages/IngestionPage'
import { GraphPage } from './pages/GraphPage'
import { MetricsPage } from './pages/MetricsPage'
import { InsightsPage } from './pages/InsightsPage'
import { SecurityPage } from './pages/SecurityPage'
import { RefactorPage } from './pages/RefactorPage'
import { ReportsPage } from './pages/ReportsPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { AdminAuditPage } from './pages/AdminAuditPage'
import { SettingsPage } from './pages/SettingsPage'
import { DesignSystemPage } from './pages/DesignSystemPage'

export default function App() {
  return (
    <ThemeProvider>
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
      <BrowserRouter>
        <AuthProvider>
          <AnalysisProvider>
            <Routes>
              {/* Public Landing Page & Design System */}
              <Route path="/" element={<WelcomePage />} />
              <Route path="/design-system" element={<DesignSystemPage />} />

              {/* Public Auth Routes */}
              <Route element={<PublicRoute />}>
                <Route path="/login" element={<AuthPage initialMode="login" />} />
                <Route path="/register" element={<AuthPage initialMode="register" />} />
              </Route>

              {/* Authenticated Application Shell */}
              <Route element={<AppLayout />}>
                {/* Dashboard (accessible to all authenticated users) */}
                <Route element={<ProtectedRoute />}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>

                {/* Developer & Senior Developer & Analyst Features */}
                <Route element={<ProtectedRoute permission="run:ingestion" />}>
                  <Route path="/ingestion" element={<IngestionPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:graph" />}>
                  <Route path="/graph" element={<GraphPage />} />
                  <Route path="/projects" element={<ProjectsPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:metrics" />}>
                  <Route path="/metrics" element={<MetricsPage />} />
                  <Route path="/insights" element={<InsightsPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:smells" />}>
                  <Route path="/security" element={<SecurityPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:refactor" />}>
                  <Route path="/refactor" element={<RefactorPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:reports" />}>
                  <Route path="/reports" element={<ReportsPage />} />
                </Route>

                {/* Engineering Manager / Admin Features */}
                <Route element={<ProtectedRoute permission="view:team_analytics" />}>
                  <Route path="/analytics" element={<AnalyticsPage />} />
                </Route>

                {/* Admin Only Features */}
                <Route element={<ProtectedRoute permission="manage:users" />}>
                  <Route path="/admin/users" element={<AdminUsersPage />} />
                </Route>

                <Route element={<ProtectedRoute permission="view:audit_logs" />}>
                  <Route path="/admin/audit" element={<AdminAuditPage />} />
                </Route>
              </Route>

              {/* Catch-all fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AnalysisProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
