import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

/**
 * Wrap any route that requires login.
 * Unauthenticated users are redirected to /login
 * and brought back here after they sign in.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  return <>{children}</>;
}

/**
 * Route that requires a specific role.
 * Unauthenticated users → /login
 * Wrong role → / (home)
 */
export function RoleRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles: string[];
}) {
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
