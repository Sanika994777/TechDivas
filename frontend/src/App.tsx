import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/shared/ProtectedRoute";

import { Navbar } from "@/components/layout/Navbar";
import { MobileTabBar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { ChatWidget } from "@/components/shared/ChatWidget";

import { LandingPage } from "@/pages/LandingPage";
import { AuthPage } from "@/pages/AuthPage";
import { ReportPage } from "@/pages/ReportPage";
import { NearbyPage } from "@/pages/NearbyPage";
import { IssueDetailPage } from "@/pages/IssueDetailPage";
import { MyComplaintsPage } from "@/pages/MyComplaintsPage";
import { TrackPage } from "@/pages/TrackPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="flex flex-col min-h-screen">
          <Navbar />

          <div className="flex-1 pb-16 md:pb-0">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<AuthPage mode="login" />} />
              <Route path="/register" element={<AuthPage mode="register" />} />
              <Route
                path="/report"
                element={
                  <ProtectedRoute>
                    <ReportPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/nearby" element={<NearbyPage />} />
              <Route path="/issues/:id" element={<IssueDetailPage />} />
              <Route path="/track" element={<TrackPage />} />

              {/* Protected — must be logged in */}
              <Route
                path="/my-complaints"
                element={
                  <ProtectedRoute>
                    <MyComplaintsPage />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>

          <Footer />
          <ChatWidget />
          <MobileTabBar />

          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                fontFamily: "Inter, sans-serif",
                borderRadius: "12px",
                border: "1px solid #E5E7EB",
                boxShadow: "0 4px 24px 0 rgba(0,0,128,0.08)",
              },
              success: { iconTheme: { primary: "#138808", secondary: "#fff" } },
              error:   { iconTheme: { primary: "#C62828", secondary: "#fff" } },
            }}
          />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
