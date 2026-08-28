import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createBrowserRouter, Navigate } from "react-router-dom";
import "./styles.css";
import { AppLayout } from "./layouts/AppLayout";
import { LoginPage } from "./features/auth/LoginPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { EquipmentListPage } from "./features/equipment/EquipmentListPage";
import { EquipmentDetailPage } from "./features/equipment/EquipmentDetailPage";
import { AlertsPage } from "./features/alerts/AlertsPage";
import { PredictionPage } from "./features/prediction/PredictionPage";
import { AutoOperationPage } from "./features/auto-operation/AutoOperationPage";
import { SensorHealthPage } from "./features/sensor-health/SensorHealthPage";
import { ReportsPage } from "./features/reports/ReportsPage";
import { RequireAuth } from "./features/auth/RequireAuth";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 15000, staleTime: 5000 } },
});

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/overview" replace /> },
      { path: "overview", element: <OverviewPage /> },
      { path: "equipment", element: <EquipmentListPage /> },
      { path: "equipment/:tag", element: <EquipmentDetailPage /> },
      { path: "alerts", element: <AlertsPage /> },
      { path: "prediction", element: <PredictionPage /> },
      { path: "auto-operation", element: <AutoOperationPage /> },
      { path: "sensor-health", element: <SensorHealthPage /> },
      { path: "reports", element: <ReportsPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
