export interface GameMetadata {
  id: string;
  title: string;
  creator: string;
  genre: 'Space Shooter' | 'Endless Runner' | 'Puzzle' | 'Platformer';
  likes: number;
  comments: number;
  thumbnailUrl: string;
  tags: string[];
}

export const MOCK_GAMES: GameMetadata[] = [
  {
    id: "1",
    title: "NEBULA DRIFTER",
    creator: "Zain_Core",
    genre: "Space Shooter",
    likes: 342,
    comments: 28,
    thumbnailUrl: "https://images.unsplash.com/photo-1614730321146-b6fa6a46bcb4?q=80&w=1000&auto=format&fit=crop",
    tags: ["2D Primary", "Bullet Hell"]
  },
  {
    id: "2",
    title: "VOID RUNNER",
    creator: "Ayaan_Sync",
    genre: "Endless Runner",
    likes: 891,
    comments: 104,
    thumbnailUrl: "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?q=80&w=1000&auto=format&fit=crop",
    tags: ["Alt-Core", "High Speed"]
  },
  {
    id: "3",
    title: "COSMIC SALVAGE",
    creator: "Guest_992",
    genre: "Space Shooter",
    likes: 156,
    comments: 12,
    thumbnailUrl: "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?q=80&w=1000&auto=format&fit=crop",
    tags: ["Tactical", "Scavenger"]
  },
  {
    id: "4",
    title: "NEON HEIST",
    creator: "CyberPunk_22",
    genre: "Platformer",
    likes: 567,
    comments: 89,
    thumbnailUrl: "https://images.unsplash.com/photo-1550684376-efcbd6e3f031?q=80&w=1000&auto=format&fit=crop",
    tags: ["Stealth", "Action"]
  },
  {
    id: "5",
    title: "ASTRO MINER",
    creator: "StarGazer",
    genre: "Endless Runner",
    likes: 234,
    comments: 45,
    thumbnailUrl: "https://images.unsplash.com/photo-1454789548928-9efd52dc4031?q=80&w=1000&auto=format&fit=crop",
    tags: ["Resource", "Survival"]
  },
  {
    id: "6",
    title: "QUANTUM LEAP",
    creator: "Physicist_Bob",
    genre: "Puzzle",
    likes: 412,
    comments: 56,
    thumbnailUrl: "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?q=80&w=1000&auto=format&fit=crop",
    tags: ["Logic", "Mind-bending"]
  }
];
