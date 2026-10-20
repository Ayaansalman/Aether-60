const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function getHeaders(token: string | null) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ─── Types ───

export interface GameData {
  game_id: string;
  user_id: string;
  game_name: string;
  genre: string;
  blueprint_json: Record<string, unknown>;
  is_public: boolean;
  is_pinned: boolean;
  plays: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  thumbnail_url?: string;
  tags: string[];
  created_at: string;
  updated_at?: string;
}

export interface UserStats {
  total_games: number;
  total_plays: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
}

export interface UserProfile {
  user_id: string;
  email?: string;
  display_name?: string;
  subscription: string;
  stats: UserStats;
  deployed_games: GameData[];
}

export interface CommentData {
  comment_id: string;
  game_id: string;
  user_id: string;
  display_name: string;
  text: string;
  created_at: string;
}

export interface AuthResponse {
  user_id: string;
  email: string;
  display_name: string;
  token: string;
}

// ─── Auth API ───

export async function registerUser(email: string, password: string, displayName: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

// ─── Games API ───

export async function fetchLibrary(token: string): Promise<GameData[]> {
  const res = await fetch(`${API_URL}/api/games/library`, {
    headers: await getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch library');
  return res.json();
}

export async function fetchPublicGames(): Promise<GameData[]> {
  const res = await fetch(`${API_URL}/api/games/`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to fetch public games');
  return res.json();
}

export async function updateGame(
  token: string,
  gameId: string,
  updates: { game_name?: string; is_pinned?: boolean; is_public?: boolean }
): Promise<GameData> {
  const res = await fetch(`${API_URL}/api/games/${gameId}`, {
    method: 'PATCH',
    headers: await getHeaders(token),
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error('Failed to update game');
  return res.json();
}

export async function deleteGame(token: string, gameId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/games/${gameId}`, {
    method: 'DELETE',
    headers: await getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to delete game');
}

// ─── Social API ───

export async function toggleLike(token: string, gameId: string): Promise<{ liked: boolean; total_likes: number }> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/like`, {
    method: 'POST',
    headers: await getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to toggle like');
  return res.json();
}

export async function checkLiked(token: string, gameId: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/liked`, {
    headers: await getHeaders(token),
  });
  if (!res.ok) return false;
  const data = await res.json();
  return data.liked;
}

export async function fetchComments(gameId: string): Promise<CommentData[]> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/comments`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to fetch comments');
  return res.json();
}

export async function postComment(token: string, gameId: string, text: string): Promise<CommentData> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/comments`, {
    method: 'POST',
    headers: await getHeaders(token),
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error('Failed to post comment');
  return res.json();
}

export async function deleteComment(token: string, gameId: string, commentId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/comments/${commentId}`, {
    method: 'DELETE',
    headers: await getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to delete comment');
}

export async function shareGame(gameId: string): Promise<{ total_shares: number }> {
  const res = await fetch(`${API_URL}/api/games/${gameId}/share`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to share game');
  return res.json();
}

// ─── User Profile API ───

export async function fetchProfile(token: string): Promise<UserProfile> {
  const res = await fetch(`${API_URL}/api/users/me`, {
    headers: await getHeaders(token),
  });
  if (!res.ok) throw new Error('Failed to fetch profile');
  return res.json();
}
