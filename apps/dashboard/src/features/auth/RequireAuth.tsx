import { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { isAuthed } from "../../lib/api";

export function RequireAuth({ children }: { children: ReactNode }) {
  if (!isAuthed()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
