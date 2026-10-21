import type Phaser from 'phaser';

/** Event cues use procedural geometry, never fabricated character frames. */
export function feedback(scene:Phaser.Scene,x:number,y:number,event:'impact'|'defeat'|'collect'|'activate'|'windup',duration=220,subtle=false){
  const counts:Record<string,number>=scene.data.get('feedback')||{};counts[event]=(counts[event]||0)+1;scene.data.set('feedback',counts);
  const color={impact:0xffa798,defeat:0xdabaff,collect:0xffe38b,activate:0x91f5c0,windup:0xff956c}[event];
  const radius=event==='windup'?24:event==='defeat'?18:10;
  const ring=scene.add.circle(x,y,radius,color,.08).setStrokeStyle(2,color,subtle?.5:.9).setDepth(2250);
  scene.tweens.add({targets:ring,scale:event==='windup'?.35:1.9,alpha:0,duration,onComplete:()=>ring.destroy()});
}
