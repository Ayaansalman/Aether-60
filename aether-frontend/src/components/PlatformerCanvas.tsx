import { useEffect, useRef, useState } from "react";
import type { PlatformerIR } from "../game/platformer/types";

export function PlatformerCanvas({
  spec,
  restart = 0,
}: {
  spec: PlatformerIR;
  restart?: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  const control = useRef<(key: string, pressed: boolean) => void>(() => {});
  const [error, setError] = useState("");
  useEffect(() => {
    let disposed = false;
    let destroy: (() => void) | undefined;
    Promise.all([
      import("phaser"),
      import("../game/platformer/PlatformerScene"),
    ])
      .then(([{ default: Phaser }, { PlatformerScene }]) => {
        if (disposed || !container.current) return;
        const game = new Phaser.Game({
          type: Phaser.AUTO,
          parent: container.current,
          width: 960,
          height: 540,
          pixelArt: true,
          scale: {
            mode: Phaser.Scale.FIT,
            autoCenter: Phaser.Scale.CENTER_BOTH,
          },
          physics: {
            default: "arcade",
            arcade: { gravity: { x: 0, y: spec.player.gravity }, debug: false },
          },
        });
        game.scene.add("Platformer", PlatformerScene, true, { spec });
        control.current = (key, pressed) => {
          game.scene
            .getScene("Platformer")
            ?.events.emit("touch-control", key, pressed);
        };
        const preventScroll = (event: KeyboardEvent) => {
          if (
            container.current?.contains(document.activeElement) &&
            [
              "Space",
              "ArrowUp",
              "ArrowDown",
              "ArrowLeft",
              "ArrowRight",
            ].includes(event.code)
          )
            event.preventDefault();
        };
        window.addEventListener("keydown", preventScroll);
        destroy = () => {
          control.current = () => {};
          window.removeEventListener("keydown", preventScroll);
          game.destroy(true);
        };
      })
      .catch((e) => setError(String(e)));
    return () => {
      disposed = true;
      destroy?.();
    };
  }, [spec, restart]);
  return (
    <>
      <div
        className="game-surface"
        ref={container}
        tabIndex={0}
        onPointerDown={(e) => e.currentTarget.focus()}
        aria-label="Playable game. Arrow keys to move, Space to jump, E to interact, F or X to shoot when equipped, R to restart"
      >
        {error && <p role="alert">Game failed to load: {error}</p>}
      </div>
      <div className="touch-controls">
        {[
          ["left", "←"],
          ["right", "→"],
          ["jump", "Jump"],
          ...(spec.player.abilities.includes("dash") ? [["dash", "Dash"]] : []),
          ...([spec,...(spec.levels || [])].some(level=>level.player_attack==='projectile') ? [['attack','Shoot']] : []),
          ...([spec,...(spec.levels || [])].some(level=>level.entities.some(entity=>entity.activation==='interact' && entity.kind==='switch')) ? [['interact','Use']] : []),
        ].map(([key, label]) => (
          <button
            key={key}
            aria-label={`Game ${key}`}
            onPointerDown={(e) => {
              e.preventDefault();
              e.currentTarget.setPointerCapture(e.pointerId);
              container.current?.focus();
              control.current(key, true);
            }}
            onPointerUp={() => control.current(key, false)}
            onPointerCancel={() => control.current(key, false)}
          >
            {label}
          </button>
        ))}
      </div>
    </>
  );
}
