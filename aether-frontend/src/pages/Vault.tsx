import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Gamepad2, Play, Eye, Heart, MessageCircle, Share2,
  Crown, Globe, Lock, Pin, Sparkles, TrendingUp,
  Zap, LogOut
} from 'lucide-react';
import { useAuthStore } from '../store/store';
import { fetchProfile } from '../lib/api';
import type { UserProfile, GameData } from '../lib/api';
import { Link, useNavigate } from 'react-router-dom';

// ─── Animated Number ───
const AnimatedNumber: React.FC<{ value: number; duration?: number }> = ({ value, duration = 800 }) => {
  const [display, setDisplay] = React.useState(0);

  useEffect(() => {
    if (value === 0) {
      const timer = setTimeout(() => setDisplay(0), 0);
      return () => clearTimeout(timer);
    }
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
  }, [value, duration]);

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString();
  };

  return <span>{formatNumber(display)}</span>;
};

// ─── Stat Tile ───
interface StatTileProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  gradient: string;
}

const StatTile: React.FC<StatTileProps> = ({ icon, label, value, gradient }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    className="group relative rounded-2xl bg-white/[0.03] border border-white/[0.06] p-6 hover:bg-white/[0.06] hover:border-white/[0.12] transition-all duration-300 overflow-hidden"
  >
    <div className={`absolute -top-10 -right-10 w-28 h-28 rounded-full blur-[50px] opacity-0 group-hover:opacity-20 transition-opacity duration-500 ${gradient}`} />
    <div className="relative z-10">
      <div className={`inline-flex p-2.5 rounded-xl bg-white/[0.04] mb-4`}>
        {icon}
      </div>
      <div className="text-3xl font-black text-white syne tracking-tight">
        <AnimatedNumber value={value} />
      </div>
      <div className="text-[10px] font-bold tracking-[0.2em] text-white/25 uppercase mt-1.5">{label}</div>
    </div>
  </motion.div>
);

const GENRE_LABELS: Record<string, string> = {
  space_shooter: 'Space Shooter',
  endless_runner: 'Endless Runner',
  puzzle: 'Puzzle',
  platformer: 'Platformer',
};

// ─── Game Row ───
const GameRow: React.FC<{ game: GameData; index: number }> = ({ game, index }) => (
  <motion.div
    initial={{ opacity: 0, x: -16 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: index * 0.05 }}
    className="group flex items-center gap-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] px-5 py-4 hover:bg-white/[0.05] hover:border-white/[0.1] transition-all duration-300"
  >
    {/* Thumbnail */}
    <div className="w-14 h-14 rounded-xl overflow-hidden flex-shrink-0 bg-black/50">
      {game.thumbnail_url ? (
        <img
          src={game.thumbnail_url}
          alt={game.game_name}
          className="w-full h-full object-cover opacity-80 group-hover:opacity-100 group-hover:scale-110 transition-all duration-500"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-primary/10">
          <Gamepad2 className="w-5 h-5 text-primary/40" />
        </div>
      )}
    </div>

    {/* Info */}
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-bold text-white/80 syne truncate">{game.game_name}</h4>
        {game.is_pinned && <Pin className="w-3 h-3 text-primary/50 flex-shrink-0" />}
        {game.is_public ? (
          <Globe className="w-3 h-3 text-emerald-400/50 flex-shrink-0" />
        ) : (
          <Lock className="w-3 h-3 text-white/20 flex-shrink-0" />
        )}
      </div>
      <div className="flex items-center gap-3 mt-1">
        <span className="text-[10px] font-bold tracking-[0.1em] text-primary/40 uppercase">
          {GENRE_LABELS[game.genre] || game.genre}
        </span>
        <span className="text-[10px] text-white/15 mono">
          {new Date(game.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>

    {/* Stats */}
    <div className="flex items-center gap-5 text-[11px] text-white/30 mono flex-shrink-0">
      <div className="flex items-center gap-1.5 min-w-[50px]">
        <Play className="w-3.5 h-3.5 text-emerald-400/40" />
        <span>{game.plays.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-1.5 min-w-[50px]">
        <Eye className="w-3.5 h-3.5 text-cyan-400/40" />
        <span>{game.views.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-1.5 min-w-[40px]">
        <Heart className="w-3.5 h-3.5 text-rose-400/40" />
        <span>{game.likes.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-1.5 min-w-[30px]">
        <MessageCircle className="w-3.5 h-3.5 text-amber-400/40" />
        <span>{game.comments}</span>
      </div>
      <div className="flex items-center gap-1.5 min-w-[30px]">
        <Share2 className="w-3.5 h-3.5 text-violet-400/40" />
        <span>{game.shares}</span>
      </div>
    </div>
  </motion.div>
);

// ─── Main Vault Page ───
export const Vault: React.FC = () => {
  const { token, user, logout } = useAuthStore();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      const timer = setTimeout(() => setLoading(true), 0);
      fetchProfile(token)
        .then(setProfile)
        .catch(() => {})
        .finally(() => setLoading(false));
      return () => clearTimeout(timer);
    }
  }, [token]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] relative">
        <div className="absolute w-[400px] h-[400px] bg-primary/8 rounded-full blur-[100px] pointer-events-none" />
        <Sparkles className="w-12 h-12 text-white/10 mb-6" />
        <h2 className="syne text-2xl font-bold text-white/60 mb-2">Access Restricted</h2>
        <p className="text-sm text-white/30 mb-8">Sign in to view your profile and games</p>
        <Link
          to="/auth"
          className="px-8 py-3 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-bold text-sm tracking-[0.1em] uppercase hover:shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all"
        >
          Initialize Core
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-8 h-8 border-2 border-white/10 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  const stats = profile?.stats || {
    total_games: 0,
    total_plays: 0,
    total_views: 0,
    total_likes: 0,
    total_comments: 0,
    total_shares: 0,
  };

  const displayName = profile?.display_name || user?.email?.split('@')[0] || 'Aether User';
  const email = profile?.email || user?.email || '';
  const subscription = profile?.subscription || 'pro';
  const initial = displayName.charAt(0).toUpperCase();
  const allGames = profile?.deployed_games || [];

  return (
    <div className="max-w-5xl mx-auto px-6 pb-24 relative">
      {/* Background */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/8 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-secondary/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Profile Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 rounded-3xl bg-white/[0.02] border border-white/[0.06] p-8 mb-8 overflow-hidden"
      >
        {/* Gradient backdrop */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5" />
        
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-6">
            {/* Avatar */}
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-black text-3xl syne shadow-[0_0_40px_rgba(99,102,241,0.3)]">
              {initial}
            </div>
            <div>
              <h1 className="syne text-3xl font-black text-white tracking-wide">{displayName}</h1>
              <p className="text-sm text-white/35 mono mt-1">{email}</p>
              <div className="flex items-center gap-3 mt-3">
                <div className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-gradient-to-r from-primary/15 to-secondary/15 border border-primary/20">
                  <Crown className="w-3.5 h-3.5 text-amber-400" />
                  <span className="text-[10px] font-black tracking-[0.15em] text-amber-400 uppercase">
                    AETHER {subscription.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/15">
                  <TrendingUp className="w-3 h-3 text-emerald-400/60" />
                  <span className="text-[10px] font-bold text-emerald-400/60">{stats.total_games} games</span>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] text-white/40 hover:text-red-400 hover:border-red-400/20 hover:bg-red-400/5 transition-all text-xs font-bold tracking-wider uppercase"
          >
            <LogOut className="w-3.5 h-3.5" />
            Logout
          </button>
        </div>
      </motion.div>

      {/* Stats Grid */}
      <div className="relative z-10 mb-8">
        <div className="flex items-center gap-2 mb-5">
          <Zap className="w-4 h-4 text-primary/40" />
          <h2 className="text-[10px] font-bold tracking-[0.25em] text-white/25 uppercase">Analytics Overview</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatTile icon={<Gamepad2 className="w-5 h-5 text-primary/50" />} label="Games" value={stats.total_games} gradient="bg-primary" />
          <StatTile icon={<Play className="w-5 h-5 text-emerald-400/50" />} label="Plays" value={stats.total_plays} gradient="bg-emerald-500" />
          <StatTile icon={<Eye className="w-5 h-5 text-cyan-400/50" />} label="Views" value={stats.total_views} gradient="bg-cyan-500" />
          <StatTile icon={<Heart className="w-5 h-5 text-rose-400/50" />} label="Likes" value={stats.total_likes} gradient="bg-rose-500" />
          <StatTile icon={<MessageCircle className="w-5 h-5 text-amber-400/50" />} label="Comments" value={stats.total_comments} gradient="bg-amber-500" />
          <StatTile icon={<Share2 className="w-5 h-5 text-violet-400/50" />} label="Shares" value={stats.total_shares} gradient="bg-violet-500" />
        </div>
      </div>

      {/* Games List */}
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Gamepad2 className="w-4 h-4 text-primary/40" />
            <h2 className="text-[10px] font-bold tracking-[0.25em] text-white/25 uppercase">Your Creations</h2>
          </div>
          <span className="text-[10px] text-white/20 mono">{allGames.length} total</span>
        </div>

        {allGames.length === 0 ? (
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.05] p-12 text-center">
            <Sparkles className="w-10 h-10 text-white/8 mx-auto mb-4" />
            <p className="text-sm text-white/25">No games created yet</p>
            <p className="text-[10px] text-white/15 mt-1 mb-6">Head to the Forge to create your first simulation</p>
            <Link
              to="/forge"
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-primary/20 text-primary text-xs font-bold tracking-wider uppercase hover:bg-primary/30 transition-all"
            >
              <Zap className="w-3.5 h-3.5" />
              Open Forge
            </Link>
          </div>
        ) : (
          <div className="space-y-2">
            {allGames.map((game, i) => (
              <GameRow key={game.game_id} game={game} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
