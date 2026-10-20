import React, { useState } from 'react';
import { GlassPanel } from './GlassPanel';
import { Heart, MessageSquare, Share2, Play, Check } from 'lucide-react';
import type { GameData } from '../lib/api';
import { toggleLike, shareGame } from '../lib/api';
import { useAuthStore } from '../store/store';
import { CommentsModal } from './CommentsModal';
import { Link } from 'react-router-dom';

interface ManifestationCardProps {
  game: GameData;
}

const GENRE_LABELS: Record<string, string> = {
  space_shooter: 'Space Shooter',
  endless_runner: 'Endless Runner',
  puzzle: 'Puzzle',
  platformer: 'Platformer',
};

export const ManifestationCard: React.FC<ManifestationCardProps> = ({ game }) => {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(game.likes);
  const [commentCount, setCommentCount] = useState(game.comments);
  const [shareCount, setShareCount] = useState(game.shares);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [shared, setShared] = useState(false);
  const { token } = useAuthStore();

  const handleLike = async () => {
    if (!token) return;
    try {
      const res = await toggleLike(token, game.game_id);
      setLiked(res.liked);
      setLikeCount(res.total_likes);
    } catch {
      // silently fail
    }
  };

  const handleShare = async () => {
    try {
      // Copy link to clipboard
      const url = `${window.location.origin}/play/${game.game_id}`;
      await navigator.clipboard.writeText(url);
      
      // Increment server-side counter
      const res = await shareGame(game.game_id);
      setShareCount(res.total_shares);
      setShared(true);
      setTimeout(() => setShared(false), 2000);
    } catch {
      // silently fail
    }
  };

  const genreLabel = GENRE_LABELS[game.genre] || game.genre;
  const thumbnailUrl = game.thumbnail_url || 'https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000&auto=format&fit=crop';
  const tags = game.tags?.length > 0 ? game.tags : [genreLabel];

  return (
    <>
      <GlassPanel hover className="group p-0 flex flex-col h-full overflow-hidden transition-all duration-500 hover:-translate-y-2">
        {/* Thumbnail Section */}
        <div className="relative h-48 overflow-hidden bg-black">
          <div className="absolute inset-0 bg-primary/20 mix-blend-overlay z-10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <img
            src={thumbnailUrl}
            alt={game.game_name}
            className="w-full h-full object-cover grayscale opacity-70 group-hover:grayscale-0 group-hover:opacity-100 group-hover:scale-110 transition-all duration-700 ease-out"
          />

          {/* Genre Badge */}
          <div className="absolute top-4 left-4 z-20">
            <span className="badge-primary shadow-[0_0_10px_rgba(99,102,241,0.5)]">
              {genreLabel}
            </span>
          </div>

          {/* Play Overlay */}
          <Link to={`/play/${game.game_id}`} className="absolute inset-0 z-30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20 hover:scale-110 hover:bg-white/20 transition-all cursor-pointer shadow-[0_0_30px_rgba(0,0,0,0.5)]">
              <Play className="w-6 h-6 text-white ml-1" fill="white" />
            </div>
          </Link>

          {/* Stats overlay */}
          <div className="absolute bottom-3 right-3 z-20 flex items-center gap-2">
            <div className="flex items-center gap-1 bg-black/50 backdrop-blur-sm rounded-md px-2 py-1">
              <Play className="w-3 h-3 text-white/60" />
              <span className="text-[10px] text-white/60 mono">{game.plays.toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="p-5 flex flex-col flex-grow relative">
          {/* Glow behind title on hover */}
          <div className="absolute top-5 left-5 w-32 h-10 bg-primary/20 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <h3 className="syne text-xl font-bold tracking-wider mb-1 relative z-10">{game.game_name}</h3>
          <p className="text-white/50 text-sm mono mb-4 relative z-10">by Ayaan</p>

          <div className="flex gap-2 mb-6 mt-auto flex-wrap">
            {tags.map((tag) => (
              <span key={tag} className="text-[10px] uppercase tracking-widest text-white/40 border border-white/10 px-2 py-1 rounded-sm">
                {tag}
              </span>
            ))}
          </div>

          {/* Footer Actions */}
          <div className="flex justify-between items-center pt-4 border-t border-white/10 mt-auto">
            <div className="flex gap-4">
              <button
                onClick={handleLike}
                className={`flex items-center gap-1.5 transition-colors group/btn ${
                  liked ? 'text-secondary' : 'text-white/50 hover:text-secondary'
                }`}
              >
                <Heart className={`w-4 h-4 ${liked ? 'fill-secondary' : 'group-hover/btn:fill-secondary/20'}`} />
                <span className="text-xs font-semibold">{likeCount}</span>
              </button>
              <button
                onClick={() => setCommentsOpen(true)}
                className="flex items-center gap-1.5 text-white/50 hover:text-primary transition-colors group/btn"
              >
                <MessageSquare className="w-4 h-4 group-hover/btn:fill-primary/20" />
                <span className="text-xs font-semibold">{commentCount}</span>
              </button>
            </div>
            <button
              onClick={handleShare}
              className={`flex items-center gap-1.5 transition-colors ${
                shared ? 'text-emerald-400' : 'text-white/30 hover:text-white'
              }`}
            >
              {shared ? <Check className="w-4 h-4" /> : <Share2 className="w-4 h-4" />}
              {shareCount > 0 && <span className="text-[10px] font-semibold">{shareCount}</span>}
            </button>
          </div>
        </div>
      </GlassPanel>

      {/* Comments Modal */}
      <CommentsModal
        isOpen={commentsOpen}
        onClose={() => setCommentsOpen(false)}
        gameId={game.game_id}
        gameName={game.game_name}
        onCommentCountChange={(delta) => setCommentCount((c) => c + delta)}
      />
    </>
  );
};
