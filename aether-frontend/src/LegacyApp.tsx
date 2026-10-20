import { Routes, Route, Link, useLocation } from "react-router-dom";
import { useAuthStore } from "./store/store";
import { useSidebarStore } from "./store/sidebarStore";
import { Nexus } from "./pages/Nexus";
import { Forge } from "./pages/Forge";
import { Auth } from "./pages/Auth";
import { Vault } from "./pages/Vault";
import { PlayGame } from "./pages/PlayGame";
import { Sidebar } from "./components/Sidebar";
import { ProfileModal } from "./components/ProfileModal";

// Landing Page
const Landing = () => (
  <div className="flex flex-col items-center justify-center min-h-screen text-center relative z-10">
    <div className="absolute w-[800px] h-[800px] bg-primary/10 rounded-full blur-[150px] pointer-events-none top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
    <h1 className="syne text-6xl md:text-8xl font-black mb-6 bg-gradient-text text-transparent bg-clip-text tracking-tighter">
      AETHER
    </h1>
    <p className="opacity-70 mb-12 max-w-xl text-lg mono tracking-wide">
      Autonomous Engine for Text-to-Heuristic Environmental Rendering
    </p>
    <div className="flex gap-6">
      <Link to="/nexus" className="btn-play">
        Browse Nexus
      </Link>
      <Link
        to="/auth"
        className="glass-panel px-10 py-4 rounded-full font-bold uppercase tracking-widest text-sm hover:bg-white/10 transition-colors border border-white/20 hover:border-white/40"
      >
        Initialize Core
      </Link>
    </div>
  </div>
);

// Layout wrapper that handles sidebar offset
const AppLayout = () => {
  const location = useLocation();
  const { isOpen } = useSidebarStore();
  const { user, logout } = useAuthStore();
  const isLanding = location.pathname === "/";
  const isAuth = location.pathname === "/auth";

  // On landing/auth pages, no sidebar offset
  const showSidebar = !isLanding && !isAuth;
  const mainMargin = showSidebar ? (isOpen ? "ml-[280px]" : "ml-[72px]") : "";
  const navMargin = showSidebar ? (isOpen ? "ml-[280px]" : "ml-[72px]") : "";

  return (
    <>
      {/* Background elements */}
      <div
        className="fixed inset-0 pointer-events-none z-[-1]"
        style={{
          background:
            "radial-gradient(circle at center, #0a0a0f 0%, #030303 100%)",
        }}
      />

      {/* Sidebar — hidden on landing and auth pages */}
      {showSidebar && <Sidebar />}
      <ProfileModal />

      {/* Navbar */}
      <nav
        className={`fixed top-0 right-0 left-0 ${navMargin} px-8 py-5 flex justify-between items-center z-30 bg-black/20 backdrop-blur-md border-b border-white/5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]`}
      >
        {isLanding || isAuth ? (
          <Link
            to="/"
            className="syne font-black text-xl tracking-[0.3em] flex items-center gap-3 group"
          >
            <div className="w-3 h-3 rounded-full bg-primary shadow-[0_0_10px_rgba(99,102,241,0.8)] group-hover:scale-125 transition-transform" />
            AETHER
          </Link>
        ) : (
          <div />
        )}
        <div className="flex items-center gap-8 text-xs font-bold tracking-[0.2em] opacity-70">
          <Link
            to="/nexus"
            className="hover:text-primary hover:opacity-100 transition-all"
          >
            NEXUS
          </Link>
          <Link
            to="/forge"
            className="hover:text-primary hover:opacity-100 transition-all"
          >
            FORGE
          </Link>
          <Link
            to="/vault"
            className="hover:text-primary hover:opacity-100 transition-all"
          >
            VAULT
          </Link>
          <div className="w-px h-4 bg-white/20 mx-2" />
          {user ? (
            <button
              onClick={logout}
              className="hover:text-red-400 transition-colors"
            >
              LOGOUT
            </button>
          ) : (
            <Link to="/auth" className="hover:text-white transition-colors">
              LOGIN
            </Link>
          )}
        </div>
      </nav>

      <main
        className={`pt-32 min-h-screen ${mainMargin} transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)]`}
      >
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/nexus" element={<Nexus />} />
          <Route path="/forge" element={<Forge />} />
          <Route path="/vault" element={<Vault />} />
          <Route path="/play/:game_id" element={<PlayGame />} />
        </Routes>
      </main>
    </>
  );
};

function App() {
  return <AppLayout />;
}

export default App;
