import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, MessageCircle, Trash2 } from 'lucide-react';
import { useAuthStore } from '../store/store';
import { fetchComments, postComment, deleteComment } from '../lib/api';
import type { CommentData } from '../lib/api';

interface CommentsModalProps {
  isOpen: boolean;
  onClose: () => void;
  gameId: string;
  gameName: string;
  onCommentCountChange: (delta: number) => void;
}

export const CommentsModal: React.FC<CommentsModalProps> = ({
  isOpen,
  onClose,
  gameId,
  gameName,
  onCommentCountChange,
}) => {
  const [comments, setComments] = useState<CommentData[]>([]);
  const [newComment, setNewComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const { token, user } = useAuthStore();
  const overlayRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && gameId) {
      const timer = setTimeout(() => setLoading(true), 0);
      fetchComments(gameId)
        .then(setComments)
        .catch(() => {})
        .finally(() => setLoading(false));
      return () => clearTimeout(timer);
    }
  }, [isOpen, gameId]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const handlePost = async () => {
    if (!token || !newComment.trim() || posting) return;
    setPosting(true);
    try {
      const comment = await postComment(token, gameId, newComment.trim());
      setComments((prev) => [comment, ...prev]);
      setNewComment('');
      onCommentCountChange(1);
    } catch {
      // silently fail
    } finally {
      setPosting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!token) return;
    try {
      await deleteComment(token, gameId, commentId);
      setComments((prev) => prev.filter((c) => c.comment_id !== commentId));
      onCommentCountChange(-1);
    } catch {
      // silently fail
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={overlayRef}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.25, ease: [0.23, 1, 0.32, 1] }}
            className="relative w-[520px] max-h-[80vh] flex flex-col rounded-3xl bg-[#0a0a12]/95 backdrop-blur-2xl border border-white/[0.08] shadow-[0_0_80px_rgba(99,102,241,0.08)]"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/[0.06]">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <MessageCircle className="w-4 h-4 text-primary/60" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white/90 syne">{gameName}</h3>
                  <p className="text-[10px] text-white/30 mono mt-0.5">{comments.length} comments</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/5 transition-colors text-white/30 hover:text-white/60"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Comments List */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 min-h-[200px] max-h-[400px]">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="w-6 h-6 border-2 border-white/10 border-t-primary rounded-full animate-spin" />
                </div>
              ) : comments.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-12">
                  <MessageCircle className="w-10 h-10 text-white/8 mb-3" />
                  <p className="text-xs text-white/25">No comments yet</p>
                  <p className="text-[10px] text-white/15 mt-1">Be the first to share your thoughts</p>
                </div>
              ) : (
                comments.map((comment) => (
                  <div key={comment.comment_id} className="group flex gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center text-[10px] font-bold text-white/60 flex-shrink-0 mt-0.5">
                      {comment.display_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white/70">{comment.display_name}</span>
                        <span className="text-[10px] text-white/20 mono">{formatDate(comment.created_at)}</span>
                        {user && comment.user_id === user.id && (
                          <button
                            onClick={() => handleDelete(comment.comment_id)}
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/10 text-white/20 hover:text-red-400 transition-all ml-auto"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                      <p className="text-xs text-white/50 mt-1 leading-relaxed">{comment.text}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input */}
            <div className="px-6 py-4 border-t border-white/[0.06]">
              {token ? (
                <div className="flex items-center gap-3">
                  <input
                    ref={inputRef}
                    type="text"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handlePost(); }}
                    placeholder="Add a comment..."
                    className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3 text-xs text-white placeholder-white/20 focus:outline-none focus:border-primary/30 transition-all"
                  />
                  <button
                    onClick={handlePost}
                    disabled={!newComment.trim() || posting}
                    className="p-3 rounded-xl bg-primary/20 hover:bg-primary/30 text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  >
                    {posting ? (
                      <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              ) : (
                <p className="text-xs text-white/25 text-center py-2">
                  <a href="/auth" className="text-primary/60 hover:text-primary underline underline-offset-4 transition-colors">Sign in</a> to comment
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
