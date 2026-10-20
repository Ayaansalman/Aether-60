import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Gamepad2,
  Play,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Crown,
  Globe,
} from 'lucide-react';
import { useSidebarStore } from '../store/sidebarStore';
import { useAuthStore } from '../store/store';

// ─── Animated Number ───
const AnimatedNumber: React.FC<{ value: number }> = ({ value }) => {
  const [display, setDisplay] = React.useState(0);

  useEffect(() => {
    if (value === 0) {
      const timer = setTimeout(() => setDisplay(0), 0);
      return () => clearTimeout(timer);
    }
    const duration = 800;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    const interval = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplay(value);
        clearInterval(interval);
      } else {
        setDisplay(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(interval);
  }, [value]);

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
  };

  return <span>{formatNumber(display)}</span>;
};

// ─── Stat Card ───
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, color }) => (
  <div className="group relative rounded-2xl bg-white/[0.03] border border-white/[0.06] p-5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-all duration-300 overflow-hidden">
    {/* Ambient glow */}
    <div className={`absolute -top-8 -right-8 w-24 h-24 rounded-full blur-[40px] opacity-0 group-hover:opacity-30 transition-opacity duration-500 ${color}`} />
    
    <div className="relative z-10">
      <div className="flex items-center gap-2 mb-3">
        <div className={`p-2 rounded-lg bg-white/5 ${color.replace('bg-', 'text-').replace('/20', '/60')}`}>
          {icon}
        </div>
      </div>
      <div className="text-2xl font-bold text-white tracking-tight syne">
        <AnimatedNumber value={value} />
      </div>
      <div className="text-[10px] font-bold tracking-[0.15em] text-white/30 uppercase mt-1">{label}</div>
    </div>
  </div>
);

// ─── Profile Modal ───
export const ProfileModal: React.FC = () => {
  const { isProfileOpen, setProfileOpen, profile } = useSidebarStore();
  const { user } = useAuthStore();
  const overlayRef = useRef<HTMLDivElement>(null);

  const displayName = profile?.display_name || user?.email?.split('@')[0] || 'Aether User';
  const email = profile?.email || user?.email || '';
  const subscription = profile?.subscription || 'pro';
  const stats = profile?.stats || {
    total_games: 0,
    total_plays: 0,
    total_views: 0,
    total_likes: 0,
    total_comments: 0,
    total_shares: 0,
  };
  const deployedGames = profile?.deployed_games || [];
  const initial = displayName.charAt(0).toUpperCase();

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setProfileOpen(false);
    };
    if (isProfileOpen) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isProfileOpen, setProfileOpen]);

  return (
    <AnimatePresence>
      {isProfileOpen && (
        <motion.div
          ref={overlayRef}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => { if (e.target === overlayRef.current) setProfileOpen(false); }}
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
            className="relative w-[680px] max-h-[85vh] overflow-y-auto rounded-3xl bg-[#0a0a12]/95 backdrop-blur-2xl border border-white/[0.08] shadow-[0_0_80px_rgba(99,102,241,0.08)]"
          >
            {/* Close button */}
            <button
              onClick={() => setProfileOpen(false)}
              className="absolute top-5 right-5 p-2 rounded-lg hover:bg-white/5 transition-colors text-white/30 hover:text-white/60 z-10"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="relative px-8 pt-8 pb-6 border-b border-white/[0.06]">
              {/* Gradient backdrop */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 rounded-t-3xl" />
              
              <div className="relative flex items-center gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-black text-2xl syne shadow-[0_0_30px_rgba(99,102,241,0.3)]">
                  {initial}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white syne tracking-wide">{displayName}</h2>
                  <p className="text-xs text-white/40 mt-0.5 mono">{email}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-primary/20 to-secondary/20 border border-primary/20">
                      <Crown className="w-3 h-3 text-amber-400" />
                      <span className="text-[10px] font-black tracking-[0.15em] text-amber-400 uppercase">
                        AETHER {subscription.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="px-8 py-6">
              <h3 className="text-[10px] font-bold tracking-[0.2em] text-white/25 uppercase mb-4">Analytics Overview</h3>
              <div className="grid grid-cols-3 gap-3">
                <StatCard
                  icon={<Gamepad2 className="w-4 h-4" />}
                  label="Deployed Games"
                  value={stats.total_games}
                  color="bg-primary/20"
                />
                <StatCard
                  icon={<Play className="w-4 h-4" />}
                  label="Total Plays"
                  value={stats.total_plays}
                  color="bg-emerald-500/20"
                />
                <StatCard
                  icon={<Eye className="w-4 h-4" />}
                  label="Total Views"
                  value={stats.total_views}
                  color="bg-cyan-500/20"
                />
                <StatCard
                  icon={<Heart className="w-4 h-4" />}
                  label="Total Likes"
                  value={stats.total_likes}
                  color="bg-rose-500/20"
                />
                <StatCard
                  icon={<MessageCircle className="w-4 h-4" />}
                  label="Comments"
                  value={stats.total_comments}
                  color="bg-amber-500/20"
                />
                <StatCard
                  icon={<Share2 className="w-4 h-4" />}
                  label="Total Shares"
                  value={stats.total_shares}
                  color="bg-violet-500/20"
                />
              </div>
            </div>

            {/* Deployed Games */}
            <div className="px-8 pb-8">
              <h3 className="text-[10px] font-bold tracking-[0.2em] text-white/25 uppercase mb-4">Deployed Games</h3>
              {deployedGames.length === 0 ? (
                <div className="rounded-2xl bg-white/[0.02] border border-white/[0.05] p-8 text-center">
                  <Globe className="w-8 h-8 text-white/10 mx-auto mb-3" />
                  <p className="text-xs text-white/30">No games deployed yet</p>
                  <p className="text-[10px] text-white/15 mt-1">Share a game from your library to deploy it</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {deployedGames.map((game) => (
                    <div
                      key={game.game_id}
                      className="flex items-center gap-4 rounded-xl bg-white/[0.02] border border-white/[0.05] px-4 py-3 hover:bg-white/[0.05] hover:border-white/[0.1] transition-all group"
                    >
                      <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Gamepad2 className="w-4 h-4 text-primary/60" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white/80 font-medium truncate">{game.game_name}</div>
                        <div className="text-[10px] text-white/25 mono mt-0.5">{game.genre}</div>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] text-white/30 mono flex-shrink-0">
                        <span className="flex items-center gap-1">
                          <Play className="w-3 h-3" /> {game.plays}
                        </span>
                        <span className="flex items-center gap-1">
                          <Eye className="w-3 h-3" /> {game.views}
                        </span>
                        <span className="flex items-center gap-1">
                          <Heart className="w-3 h-3" /> {game.likes}
                        </span>
                        <span className="flex items-center gap-1">
                          <MessageCircle className="w-3 h-3" /> {game.comments}
                        </span>
                        <span className="flex items-center gap-1">
                          <Share2 className="w-3 h-3" /> {game.shares}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
