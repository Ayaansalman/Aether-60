import React, { useEffect, useState } from 'react';
import { fetchPublicGames } from '../lib/api';
import type { GameData } from '../lib/api';
import { ManifestationCard } from '../components/ManifestationCard';
import { Sparkles, Search, Filter, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Nexus: React.FC = () => {
  const [games, setGames] = useState<GameData[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchPublicGames()
      .then(setGames)
      .catch(() => setError('Failed to load games'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = games.filter(
    (g) =>
      g.game_name.toLowerCase().includes(search.toLowerCase()) ||
      g.genre.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-6 pb-24 relative min-h-screen">
      {/* Background ambient light */}
      <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-[600px] h-[600px] bg-secondary/5 rounded-full blur-[150px] pointer-events-none" />

      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-end gap-6 mb-12 relative z-10">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="text-primary w-6 h-6" />
            <h1 className="syne text-4xl font-bold tracking-widest">NEXUS</h1>
          </div>
          <p className="text-white/50 mono text-sm">COMMUNITY MANIFESTATION GALLERY</p>
        </div>

        <div className="flex gap-4 w-full md:w-auto">
          <div className="relative flex-grow md:flex-grow-0">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
            <input
              type="text"
              placeholder="Search simulations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full md:w-64 bg-white/5 border border-white/10 rounded-full py-3 pl-12 pr-6 text-sm text-white placeholder-white/40 focus:outline-none focus:border-primary/50 focus:bg-white/10 transition-all"
            />
          </div>
          <button className="flex items-center justify-center w-12 h-12 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/30 transition-all">
            <Filter className="w-4 h-4 text-white/70" />
          </button>
          <Link to="/forge" className="flex items-center justify-center px-6 rounded-full bg-primary text-white font-bold text-sm tracking-widest hover:bg-primary/80 hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-all uppercase">
            Create
          </Link>
        </div>
      </div>

      {/* Grid Section */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-primary/40 animate-spin" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-white/30 text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 text-xs text-primary/60 hover:text-primary transition-colors underline underline-offset-4"
          >
            Retry
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64">
          <Sparkles className="w-10 h-10 text-white/10 mb-3" />
          <p className="text-white/30 text-sm">No simulations found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 relative z-10">
          {filtered.map((game) => (
            <ManifestationCard key={game.game_id} game={game} />
          ))}
        </div>
      )}
    </div>
  );
};
