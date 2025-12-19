import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import Translate from "./pages/Translate";
import Practice from "./pages/Practice";
import History from "./pages/History";
import Profile from "./pages/Profile";
import LanguageSetup from "./components/LanguageSetup";
import Login from "./pages/Login";
import "./App.css";

// Protected Route wrapper - redirects to login if not authenticated
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function App() {
  const { user, loading } = useAuth();

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  // Check if user needs onboarding (logged in but no languages set)
  const needsOnboarding =
    user &&
    (!user.translator_languages || user.translator_languages.length === 0);

  if (needsOnboarding) {
    return <LanguageSetup />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/translate" replace /> : <Login />}
        />
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/translate" replace />} />
          {/* Public route - accessible to everyone */}
          <Route path="translate" element={<Translate />} />
          {/* Protected routes - require authentication */}
          <Route
            path="practice"
            element={
              <ProtectedRoute>
                <Practice />
              </ProtectedRoute>
            }
          />
          <Route
            path="history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />
          <Route
            path="profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/translate" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
