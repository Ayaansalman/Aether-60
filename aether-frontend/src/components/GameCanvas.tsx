import React, { useEffect, useRef } from 'react';
import Phaser from 'phaser';
import { ArenaScene } from '../game/ArenaScene';
import type { GameIR } from '../game/gameir';

interface GameCanvasProps {
  gameIR: GameIR;
}

export const GameCanvas: React.FC<GameCanvasProps> = ({ gameIR }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Phaser.Game | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const config: Phaser.Types.Core.GameConfig = {
      type: Phaser.AUTO,
      parent: containerRef.current,
      width: 800,
      height: 600,
      backgroundColor: '#0a0a14',
      physics: {
        default: 'arcade',
        arcade: {
          gravity: { x: 0, y: 0 },
          debug: false,
        },
      },
    };

    const game = new Phaser.Game(config);
    game.scene.add('ArenaScene', ArenaScene, true, { gameIR });
    gameRef.current = game;

    return () => {
      if (gameRef.current) {
        gameRef.current.destroy(true);
        gameRef.current = null;
      }
    };
  }, [gameIR]);

  return (
    <div className="flex flex-col items-center justify-center">
      <div
        ref={containerRef}
        className="w-[800px] h-[600px] rounded-2xl overflow-hidden border border-white/10 shadow-[0_0_50px_rgba(99,102,241,0.2)] bg-[#0a0a14]"
      />
    </div>
  );
};
