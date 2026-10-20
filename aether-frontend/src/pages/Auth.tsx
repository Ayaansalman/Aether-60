import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Zap, ArrowRight, Sparkles } from 'lucide-react';
import { useAuthStore } from '../store/store';
import { loginUser, registerUser } from '../lib/api';

export const Auth: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      let res;
      if (isLogin) {
        res = await loginUser(email, password);
      } else {
        res = await registerUser(email, password, displayName);
      }

      setUser(
        { id: res.user_id, email: res.email, role: 'authenticated' },
        res.token
      );
      navigate('/nexus');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh] relative">
      {/* Background effects */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/8 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-secondary/5 rounded-full blur-[100px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
        className="w-full max-w-md relative z-10"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-primary shadow-[0_0_15px_rgba(99,102,241,0.8)]" />
            <span className="syne font-black text-2xl tracking-[0.3em] text-white/90">AETHER</span>
          </div>
          <p className="text-white/40 text-sm mono tracking-wider">
            {isLogin ? 'WELCOME BACK, OPERATOR' : 'INITIALIZE NEW IDENTITY'}
          </p>
        </div>

        {/* Form Card */}
        <div className="rounded-3xl bg-white/[0.03] backdrop-blur-2xl border border-white/[0.08] p-8 shadow-[0_0_60px_rgba(0,0,0,0.3)]">
          {/* Toggle */}
          <div className="flex rounded-xl bg-white/[0.03] border border-white/[0.06] p-1 mb-8">
            <button
              onClick={() => { setIsLogin(true); setError(''); }}
              className={`flex-1 py-2.5 rounded-lg text-xs font-bold tracking-[0.15em] uppercase transition-all ${
                isLogin ? 'bg-primary/20 text-primary border border-primary/20' : 'text-white/40 hover:text-white/60'
              }`}
            >
              Login
            </button>
            <button
              onClick={() => { setIsLogin(false); setError(''); }}
              className={`flex-1 py-2.5 rounded-lg text-xs font-bold tracking-[0.15em] uppercase transition-all ${
                !isLogin ? 'bg-primary/20 text-primary border border-primary/20' : 'text-white/40 hover:text-white/60'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <AnimatePresence mode="wait">
              {!isLogin && (
                <motion.div
                  key="displayName"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <label className="block text-[10px] font-bold tracking-[0.2em] text-white/30 uppercase mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Enter your name"
                    className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-primary/40 focus:bg-white/[0.06] transition-all"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label className="block text-[10px] font-bold tracking-[0.2em] text-white/30 uppercase mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@aether.io"
                required
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-primary/40 focus:bg-white/[0.06] transition-all"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold tracking-[0.2em] text-white/30 uppercase mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-3.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-primary/40 focus:bg-white/[0.06] transition-all pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-white/5 transition-colors text-white/30 hover:text-white/60"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs text-red-400"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-xl bg-gradient-to-r from-primary to-secondary text-white font-bold text-sm tracking-[0.1em] uppercase hover:shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  {isLogin ? 'ACCESS CORE' : 'INITIALIZE'}
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Footer hint */}
          <div className="mt-6 text-center">
            <p className="text-[10px] text-white/20 mono">
              {isLogin ? "Don't have an account? " : 'Already initialized? '}
              <button
                onClick={() => { setIsLogin(!isLogin); setError(''); }}
                className="text-primary/60 hover:text-primary transition-colors underline underline-offset-4"
              >
                {isLogin ? 'Register' : 'Login'}
              </button>
            </p>
          </div>
        </div>

        {/* Test credentials hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] px-5 py-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-3 h-3 text-amber-400/60" />
            <span className="text-[10px] font-bold tracking-[0.15em] text-amber-400/60 uppercase">Test Credentials</span>
          </div>
          <div className="text-xs text-white/30 mono space-y-1">
            <p>Email: <span className="text-white/50">ayaan@test.com</span></p>
            <p>Pass:  <span className="text-white/50">test123</span></p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};
