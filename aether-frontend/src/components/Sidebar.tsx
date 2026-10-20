import React, { useEffect, useState, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Pin,
  PinOff,
  Pencil,
  Trash2,
  MoreHorizontal,
  Gamepad2,
  Sparkles,
  Crown,
  ChevronRight,
} from 'lucide-react';
import { useSidebarStore } from '../store/sidebarStore';
import { useAuthStore } from '../store/store';
import type { GameData } from '../lib/api';

// ─── Date grouping helper ───
function groupByDate(games: GameData[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const pinned: GameData[] = [];
  const todayGames: GameData[] = [];
  const yesterdayGames: GameData[] = [];
  const weekGames: GameData[] = [];
  const olderGames: GameData[] = [];

  for (const game of games) {
    if (game.is_pinned) {
      pinned.push(game);
      continue;
    }
    const d = new Date(game.created_at);
    if (d >= today) todayGames.push(game);
    else if (d >= yesterday) yesterdayGames.push(game);
    else if (d >= weekAgo) weekGames.push(game);
    else olderGames.push(game);
  }

  return { pinned, todayGames, yesterdayGames, weekGames, olderGames };
}

// ─── Context Menu ───
interface ContextMenuProps {
  game: GameData;
  onClose: () => void;
  onPin: () => void;
  onRename: () => void;
  onDelete: () => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ game, onClose, onPin, onRename, onDelete }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, scale: 0.9, y: -4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.12 }}
      className="absolute right-0 top-full mt-1 z-[100] min-w-[160px] rounded-xl border border-white/10 bg-[#0d0d14]/95 backdrop-blur-xl shadow-2xl overflow-hidden"
    >
      <button
        onClick={onPin}
        className="flex items-center gap-3 w-full px-4 py-2.5 text-xs text-white/70 hover:bg-white/5 hover:text-white transition-colors"
      >
        {game.is_pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
        {game.is_pinned ? 'Unpin' : 'Pin to top'}
      </button>
      <button
        onClick={onRename}
        className="flex items-center gap-3 w-full px-4 py-2.5 text-xs text-white/70 hover:bg-white/5 hover:text-white transition-colors"
      >
        <Pencil className="w-3.5 h-3.5" />
        Rename
      </button>
      <div className="h-px bg-white/5 mx-2" />
      <button
        onClick={onDelete}
        className="flex items-center gap-3 w-full px-4 py-2.5 text-xs text-red-400/80 hover:bg-red-500/10 hover:text-red-400 transition-colors"
      >
        <Trash2 className="w-3.5 h-3.5" />
        Delete
      </button>
    </motion.div>
  );
};

// ─── Game Item ───
interface GameItemProps {
  game: GameData;
  collapsed: boolean;
}

const GameItem: React.FC<GameItemProps> = ({ game, collapsed }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(game.game_name);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { pinGame, renameGame, removeGame } = useSidebarStore();
  const { token } = useAuthStore();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isRenaming && inputRef.current) inputRef.current.focus();
  }, [isRenaming]);

  const handleRename = () => {
    if (token && renameValue.trim() && renameValue !== game.game_name) {
      renameGame(token, game.game_id, renameValue.trim());
    }
    setIsRenaming(false);
    setMenuOpen(false);
  };

  const handleDelete = () => {
    if (confirmDelete && token) {
      removeGame(token, game.game_id);
      setConfirmDelete(false);
    } else {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
    }
    setMenuOpen(false);
  };

  if (collapsed) {
    return (
      <div className="group relative flex items-center justify-center py-2" title={game.game_name}>
        <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-white/40 group-hover:bg-primary/10 group-hover:text-primary transition-colors cursor-pointer">
          <Gamepad2 className="w-4 h-4" />
        </div>
      </div>
    );
  }

  return (
    <div className="group relative">
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
        {game.is_pinned && <Pin className="w-3 h-3 text-primary/60 flex-shrink-0" />}
        <Gamepad2 className="w-3.5 h-3.5 text-white/30 flex-shrink-0" />
        
        {isRenaming ? (
          <input
            ref={inputRef}
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onBlur={handleRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRename();
              if (e.key === 'Escape') { setIsRenaming(false); setRenameValue(game.game_name); }
            }}
            className="flex-1 min-w-0 bg-white/5 border border-primary/30 rounded-md px-2 py-0.5 text-xs text-white outline-none"
          />
        ) : (
          <span className="flex-1 min-w-0 truncate text-xs text-white/60 group-hover:text-white/90 transition-colors">
            {game.game_name}
          </span>
        )}

        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen(!menuOpen); }}
          className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-white/10 transition-all flex-shrink-0"
        >
          <MoreHorizontal className="w-3.5 h-3.5 text-white/50" />
        </button>
      </div>

      <AnimatePresence>
        {menuOpen && (
          <ContextMenu
            game={game}
            onClose={() => setMenuOpen(false)}
            onPin={() => { if (token) pinGame(token, game.game_id, !game.is_pinned); setMenuOpen(false); }}
            onRename={() => { setIsRenaming(true); setMenuOpen(false); }}
            onDelete={handleDelete}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {confirmDelete && !menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-3 pb-2"
          >
            <div className="flex items-center gap-2 text-[10px] text-red-400/80">
              <span>Delete this game?</span>
              <button
                onClick={() => { if (token) removeGame(token, game.game_id); }}
                className="px-2 py-0.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors"
              >
                Confirm
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 text-white/40 transition-colors"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─── Section ───
interface SectionProps {
  title: string;
  games: GameData[];
  collapsed: boolean;
}

const Section: React.FC<SectionProps> = ({ title, games, collapsed }) => {
  if (games.length === 0) return null;

  return (
    <div className="mb-2">
      {!collapsed && (
        <div className="px-4 py-1.5">
          <span className="text-[10px] font-bold tracking-[0.15em] text-white/25 uppercase">{title}</span>
        </div>
      )}
      {games.map((game) => (
        <GameItem key={game.game_id} game={game} collapsed={collapsed} />
      ))}
    </div>
  );
};

// ─── Profile Button ───
interface ProfileButtonProps {
  collapsed: boolean;
}

const ProfileButton: React.FC<ProfileButtonProps> = ({ collapsed }) => {
  const { toggleProfile, profile } = useSidebarStore();
  const { user } = useAuthStore();

  const displayName = profile?.display_name || user?.email?.split('@')[0] || 'Aether User';
  const subscription = profile?.subscription || 'pro';
  const initial = displayName.charAt(0).toUpperCase();

  if (collapsed) {
    return (
      <button
        onClick={toggleProfile}
        className="w-full flex justify-center py-3 group"
        title={displayName}
      >
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-sm group-hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-shadow">
          {initial}
        </div>
      </button>
    );
  }

  return (
    <button
      onClick={toggleProfile}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors group"
    >
      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-bold text-sm flex-shrink-0 group-hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-shadow">
        {initial}
      </div>
      <div className="flex-1 min-w-0 text-left">
        <div className="text-sm text-white/90 truncate font-medium">{displayName}</div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <Crown className="w-3 h-3 text-amber-400" />
          <span className="text-[10px] font-bold tracking-[0.1em] text-amber-400/80 uppercase">
            AETHER {subscription.toUpperCase()}
          </span>
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/40 transition-colors flex-shrink-0" />
    </button>
  );
};

// ─── Main Sidebar ───
export const Sidebar: React.FC = () => {
  const { isOpen, toggleSidebar, games, loadGames, loadProfile } = useSidebarStore();
  const { token } = useAuthStore();
  const location = useLocation();

  // Load data when user is authenticated
  useEffect(() => {
    if (token) {
      loadGames(token);
      loadProfile(token);
    }
  }, [token, loadGames, loadProfile]);

  const { pinned, todayGames, yesterdayGames, weekGames, olderGames } = groupByDate(games);

  // Hide on landing page
  if (location.pathname === '/') return null;

  return (
    <motion.aside
      initial={false}
      animate={{ width: isOpen ? 280 : 72 }}
      transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
      className="fixed left-0 top-0 h-screen z-40 flex flex-col bg-[#060609]/80 backdrop-blur-2xl border-r border-white/[0.06]"
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-white/[0.06]">
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2"
          >
            <Link to="/" className="flex items-center gap-2 group">
              <div className="w-2.5 h-2.5 rounded-full bg-primary shadow-[0_0_10px_rgba(99,102,241,0.8)] group-hover:scale-125 transition-transform" />
              <span className="syne font-black text-sm tracking-[0.3em] text-white/90">AETHER</span>
            </Link>
          </motion.div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-white/5 transition-colors text-white/40 hover:text-white/70"
        >
          {isOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </button>
      </div>

      {/* New Game button */}
      <div className="px-3 py-3">
        <Link
          to="/forge"
          className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border border-white/10 hover:border-primary/30 hover:bg-primary/5 transition-all group ${
            isOpen ? 'px-4' : 'px-0'
          }`}
        >
          <Plus className="w-4 h-4 text-white/50 group-hover:text-primary transition-colors" />
          {isOpen && (
            <span className="text-xs font-bold tracking-[0.1em] text-white/50 group-hover:text-primary uppercase transition-colors">
              New Game
            </span>
          )}
        </Link>
      </div>

      {/* Game List */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-1 scrollbar-thin">
        {!token ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            {isOpen && (
              <div className="text-center">
                <Sparkles className="w-8 h-8 text-white/10 mx-auto mb-3" />
                <p className="text-xs text-white/30 mb-4">Sign in to see your games</p>
                <Link
                  to="/auth"
                  className="text-xs text-primary/60 hover:text-primary transition-colors underline underline-offset-4"
                >
                  Login
                </Link>
              </div>
            )}
          </div>
        ) : games.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            {isOpen && (
              <div className="text-center">
                <Gamepad2 className="w-8 h-8 text-white/10 mx-auto mb-3" />
                <p className="text-xs text-white/30">No games yet</p>
                <p className="text-[10px] text-white/20 mt-1">Create one in the Forge</p>
              </div>
            )}
          </div>
        ) : (
          <>
            <Section title="Pinned" games={pinned} collapsed={!isOpen} />
            <Section title="Today" games={todayGames} collapsed={!isOpen} />
            <Section title="Yesterday" games={yesterdayGames} collapsed={!isOpen} />
            <Section title="Previous 7 Days" games={weekGames} collapsed={!isOpen} />
            <Section title="Older" games={olderGames} collapsed={!isOpen} />
          </>
        )}
      </div>

      {/* Profile */}
      <div className="border-t border-white/[0.06]">
        <ProfileButton collapsed={!isOpen} />
      </div>
    </motion.aside>
  );
};
