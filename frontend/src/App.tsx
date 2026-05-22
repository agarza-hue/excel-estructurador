import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import CapturePage from "./pages/CapturePage";
import ConfigPage from "./pages/ConfigPage";
import DashboardPage from "./pages/DashboardPage";
import ExplorerPage from "./pages/ExplorerPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/capture" element={<CapturePage />} />
        <Route path="/explorer" element={<ExplorerPage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Route>
    </Routes>
  );
}
