import React, { useEffect, useRef } from 'react';
import { GlassPanel } from './GlassPanel';
import { Terminal as TerminalIcon } from 'lucide-react';

export type LogLevel = 'info' | 'success' | 'warning' | 'error';

export interface TerminalLog {
  id: string;
  timestamp: string;
  message: string;
  level: LogLevel;
}

interface SystemTerminalProps {
  logs: TerminalLog[];
}

export const SystemTerminal: React.FC<SystemTerminalProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const getLevelStyle = (level: LogLevel) => {
    switch (level) {
      case 'success': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'error': return 'text-red-400';
      default: return 'text-white/70';
    }
  };

  return (
    <GlassPanel className="h-full flex flex-col p-4 bg-black/40 border-t-primary/30">
      <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
        <TerminalIcon className="w-4 h-4 text-primary" />
        <span className="mono text-xs font-bold tracking-widest text-white/50">SYSTEM_TERMINAL_v3.0</span>
      </div>
      
      <div 
        ref={scrollRef}
        className="flex-grow overflow-y-auto space-y-1 mono text-[11px] md:text-xs"
      >
        {logs.length === 0 ? (
          <div className="text-white/30 italic">Awaiting input stream...</div>
        ) : (
          logs.map(log => (
            <div key={log.id} className="flex gap-3 leading-relaxed hover:bg-white/5 px-2 py-0.5 rounded transition-colors">
              <span className="text-white/30 whitespace-nowrap">[{log.timestamp}]</span>
              <span className={getLevelStyle(log.level)}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </GlassPanel>
  );
};
