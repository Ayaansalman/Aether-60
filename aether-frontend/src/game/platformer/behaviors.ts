/** Pure decisions shared by runtime components and regression tests. Physics remains Phaser-owned. */
export type IcicleState = "waiting" | "warning" | "falling" | "spent";
export function iciclePhase(state: IcicleState, elapsed: number, near: boolean, trigger: string, period: number): IcicleState {
  if (state === "waiting" && (trigger === "timer" ? elapsed >= period : near)) return "warning";
  if (state === "warning" && elapsed >= 450) return "falling";
  if (state === "spent" && elapsed >= period) return "waiting";
  return state;
}

export function enemyDecision(behavior: string, x: number, y: number, low: number, high: number,
  previousDirection: number, playerX: number, playerY: number, elapsedSinceShot: number) {
  let direction = x < low ? 1 : x > high ? -1 : previousDirection;
  const dx = playerX - x, inLane = Math.abs(playerY - y) < 100;
  if (behavior === "shooter") return {direction: Math.sign(dx) || direction, vx: 0,
    fire: Math.abs(dx) < 400 && inLane && elapsedSinceShot >= 1400};
  if (behavior === "chase" && Math.abs(dx) < 230 && inLane) {
    direction = dx < 0 ? -1 : 1;
    return {direction, vx: (direction < 0 && x <= low || direction > 0 && x >= high) ? 0 : direction * 125, fire: false};
  }
  return {direction, vx: direction * 65, fire: false};
}

export function indicatorAnimation(mode: string | undefined) {
  return !mode || mode === "none" ? null : {alpha: mode === "flash" ? .15 : .5, duration: mode === "flash" ? 220 : 850};
}

export function exitDecision(level: number, count: number, collected: number, required: number) {
  return collected < required ? "locked" : level + 1 < count ? "next" : "won";
}
