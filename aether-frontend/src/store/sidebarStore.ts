import { create } from 'zustand';
import type { GameData, UserProfile } from '../lib/api';
import { fetchLibrary, updateGame, deleteGame, fetchProfile } from '../lib/api';

interface SidebarState {
  // UI state
  isOpen: boolean;
  isProfileOpen: boolean;
  
  // Data
  games: GameData[];
  profile: UserProfile | null;
  isLoading: boolean;
  error: string | null;
  
  // UI actions
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleProfile: () => void;
  setProfileOpen: (open: boolean) => void;
  
  // Data actions
  loadGames: (token: string) => Promise<void>;
  loadProfile: (token: string) => Promise<void>;
  pinGame: (token: string, gameId: string, pinned: boolean) => Promise<void>;
  renameGame: (token: string, gameId: string, newName: string) => Promise<void>;
  removeGame: (token: string, gameId: string) => Promise<void>;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  isOpen: true,
  isProfileOpen: false,
  games: [],
  profile: null,
  isLoading: false,
  error: null,

  toggleSidebar: () => set((s) => ({ isOpen: !s.isOpen })),
  setSidebarOpen: (open) => set({ isOpen: open }),
  toggleProfile: () => set((s) => ({ isProfileOpen: !s.isProfileOpen })),
  setProfileOpen: (open) => set({ isProfileOpen: open }),

  loadGames: async (token: string) => {
    set({ isLoading: true, error: null });
    try {
      const games = await fetchLibrary(token);
      set({ games, isLoading: false });
    } catch {
      set({ error: 'Failed to load games', isLoading: false });
    }
  },

  loadProfile: async (token: string) => {
    try {
      const profile = await fetchProfile(token);
      set({ profile });
    } catch {
      set({ error: 'Failed to load profile' });
    }
  },

  pinGame: async (token: string, gameId: string, pinned: boolean) => {
    try {
      await updateGame(token, gameId, { is_pinned: pinned });
      // Optimistic update
      set((s) => ({
        games: s.games.map((g) =>
          g.game_id === gameId ? { ...g, is_pinned: pinned } : g
        ),
      }));
    } catch {
      set({ error: 'Failed to pin game' });
    }
  },

  renameGame: async (token: string, gameId: string, newName: string) => {
    try {
      await updateGame(token, gameId, { game_name: newName });
      set((s) => ({
        games: s.games.map((g) =>
          g.game_id === gameId ? { ...g, game_name: newName } : g
        ),
      }));
    } catch {
      set({ error: 'Failed to rename game' });
    }
  },

  removeGame: async (token: string, gameId: string) => {
    try {
      await deleteGame(token, gameId);
      set((s) => ({
        games: s.games.filter((g) => g.game_id !== gameId),
      }));
    } catch {
      set({ error: 'Failed to delete game' });
    }
  },
}));
