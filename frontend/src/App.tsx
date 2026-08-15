import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { MainLayout } from './components/layout/MainLayout';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { VendorsPage } from './features/vendors/VendorsPage';
import { MonitoringPage } from './features/monitoring/MonitoringPage';
import { RiskAnalyticsPage } from './features/risk-analytics/RiskAnalyticsPage';
import { TimelinePage } from './features/timeline/TimelinePage';
import { CompliancePage } from './features/compliance/CompliancePage';
import { AlertsPage } from './features/alerts/AlertsPage';
import { ReportsPage } from './features/reports/ReportsPage';
import { AssistantPage } from './features/assistant/AssistantPage';
import { SettingsPage } from './features/settings/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 mins
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="vendors" element={<VendorsPage />} />
            <Route path="monitoring" element={<MonitoringPage />} />
            <Route path="risk-analytics" element={<RiskAnalyticsPage />} />
            <Route path="timeline" element={<TimelinePage />} />
            <Route path="compliance" element={<CompliancePage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="assistant" element={<AssistantPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
