import { lazy, Suspense } from "react";
import { BrowserRouter, useLocation } from "react-router-dom";
const Studio = lazy(() => import("./pages/Studio"));
const LegacyApp = lazy(() => import("./LegacyApp"));
function Content() {
  const path = useLocation().pathname;
  const studio =
    path === "/" || path === "/forge" || path.startsWith("/studio");
  return (
    <Suspense
      fallback={
        <div
          style={{
            padding: 40,
            background: "#fafbf8",
            color: "#34745b",
            minHeight: "100vh",
          }}
        >
          Opening Aether…
        </div>
      }
    >
      {studio ? <Studio /> : <LegacyApp />}
    </Suspense>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <Content />
    </BrowserRouter>
  );
}
