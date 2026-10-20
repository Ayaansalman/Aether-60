import React, { type ReactNode } from 'react';
import { cn } from '../lib/utils';

interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  borderAccent?: boolean;
}

export const GlassPanel: React.FC<GlassPanelProps> = ({ 
  children, 
  className, 
  hover = false,
  borderAccent = false,
  ...props 
}) => {
  return (
    <div 
      className={cn(
        "glass-panel rounded-3xl p-6 relative overflow-hidden",
        hover && "hover:shadow-[0_0_30px_rgba(99,102,241,0.15)] hover:border-primary/30",
        borderAccent && "border-t-primary/50",
        className
      )}
      {...props}
    >
      {/* Subtle top glare effect */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      {children}
    </div>
  );
};
