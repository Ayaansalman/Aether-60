import type {RunnerWorld,RunnerIR} from './world.ts';

// Shared CC0 Kenney atlases, all environment tiles 18px at 2x nearest-neighbor.
// Ice, neon accents, woodland fox and bird are original pixel primitives.
export const ARCADE_ART={
  forest:{sky:'#b8dfcc',horizon:'#5f9c89',ground:'#544c47',accent:'#f4d78b',atlas:'terrain',tile:0,background:'forest'},
  factory:{sky:'#222b3d',horizon:'#4b5961',ground:'#26313c',accent:'#ffbb59',atlas:'industrial',tile:0,background:'industrial'},
  neon:{sky:'#161737',horizon:'#393767',ground:'#252b48',accent:'#60f1d2',atlas:'industrial',tile:0,background:'twilight'},
  ice:{sky:'#152e51',horizon:'#386983',ground:'#b3dced',accent:'#b8f5ff',atlas:'terrain',tile:42,background:''},
  sky:{sky:'#7dc7df',horizon:'#c4ebee',ground:'#d9cfa4',accent:'#fff2b3',atlas:'terrain',tile:2,background:''},
} as const;

export class ArcadePainter {
  images:Record<string,HTMLImageElement>={};
  constructor(theme:RunnerIR['theme'],player:RunnerIR['player']){
    const art=ARCADE_ART[theme];
    const files:Record<string,string>={[art.atlas]:art.atlas+'.png'};
    if(player==='robot')files.characters='characters.png';
    if(art.background)files[art.background==='industrial'?'industrialBg':art.background]='background-'+art.background+'.png';
    for(const [key,path] of Object.entries(files)){const im=new Image();im.src='/assets/platformer/'+path;this.images[key]=im;}
  }
  tile(ctx:CanvasRenderingContext2D,atlas:string,index:number,x:number,y:number,width=36,height=36){
    const im=this.images[atlas],size=atlas==='characters'?24:18,columns=atlas==='industrial'?16:atlas==='characters'?9:20;
    if(im?.complete&&im.naturalWidth)ctx.drawImage(im,(index%columns)*size,Math.floor(index/columns)*size,size,size,Math.round(x),Math.round(y),width,height);
  }
  draw(ctx:CanvasRenderingContext2D,w:RunnerWorld,now:number){
    const s=w.spec,art=ARCADE_ART[s.theme],d=w.distance;
    ctx.imageSmoothingEnabled=false;
    const gradient=ctx.createLinearGradient(0,0,0,540);gradient.addColorStop(0,art.sky);gradient.addColorStop(1,art.horizon);ctx.fillStyle=gradient;ctx.fillRect(0,0,960,540);
    const background=this.images[art.background==='industrial'?'industrialBg':art.background];
    if(background?.complete&&background.naturalWidth){ctx.globalAlpha=.5;for(let x=-((d*.12)%288);x<960;x+=288)ctx.drawImage(background,x,108,288,432);ctx.globalAlpha=1;}
    for(let layer=0;layer<2;layer++)for(let i=0;i<11;i++){
      const x=((i*124-d*(layer?.32:.16))%1364+1364)%1364-150,y=190+(i*37%110);
      if(s.theme==='forest'){
        ctx.fillStyle=layer?'#386c62':'#4e8574';ctx.fillRect(x+38,y,14,350);ctx.fillStyle=layer?'#3a806b':'#659d7e';
        for(let k=0;k<3;k++){ctx.fillRect(x+12-k*6,y+26+k*26,68+k*12,40);}ctx.fillStyle='#a9c79a';ctx.fillRect(x+18,y+32,12,4);
      }else if(s.theme==='factory'){
        ctx.fillStyle=layer?'#374650':'#3f505e';ctx.fillRect(x+20,y-30,62,350);ctx.fillStyle='#657479';ctx.fillRect(x+24,y-24,7,338);ctx.fillRect(x,y+60,124,9);
        ctx.fillStyle=art.accent;for(let k=0;k<3;k++)ctx.fillRect(x+46,y+28+k*52,18,5);
        if(layer){ctx.strokeStyle='#6f8589';ctx.lineWidth=6;ctx.beginPath();ctx.arc(x+58,y+135,24,now/2000,now/2000+5);ctx.stroke();}
      }else if(s.theme==='ice'){
        ctx.fillStyle=layer?'#548ca2':'#2b5576';ctx.beginPath();ctx.moveTo(x,540);ctx.lineTo(x+25,300);ctx.lineTo(x+55,210+i%3*25);ctx.lineTo(x+115,540);ctx.fill();
        ctx.fillStyle='#6093ae';ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x+36,124+i%3*25);ctx.lineTo(x+92,0);ctx.fill();ctx.fillStyle='#c1f6fa';ctx.fillRect(x+48,310,4,60);
      }else if(s.theme==='sky'){
        ctx.fillStyle=layer?'#ffffffbf':'#d8f2f3a0';ctx.fillRect(x,y,100,20);ctx.fillRect(x+16,y-14,66,46);ctx.fillRect(x+36,y-24,28,60);
      }else{
        ctx.fillStyle=layer?'#292b50':'#292346';ctx.fillRect(x,y-80,82,410);ctx.fillStyle=i%2?'#da68c1':'#65cbd3';for(let k=0;k<5;k++)ctx.fillRect(x+12+(k%2)*24,y-54+k*40,10,12);
        if(layer&&i%3===0){ctx.strokeStyle='#ee6ea7';ctx.lineWidth=3;ctx.strokeRect(x+4,y+55,64,30);}
      }
    }
    if(s.mode==='ground'){
      ctx.fillStyle=art.ground;ctx.fillRect(0,444,960,96);
      for(let x=-d%36;x<960;x+=36){
        if(s.theme==='ice'){ctx.fillStyle='#edfaff';ctx.fillRect(x,444,36,9);ctx.fillStyle='#77afcb';ctx.fillRect(x+8,466,2,32);ctx.fillRect(x+10,496,18,2);}
        else {this.tile(ctx,art.atlas,art.tile,x,444);this.tile(ctx,art.atlas,s.theme==='forest'?4:art.tile,x,480);}
      }
      ctx.fillStyle=art.accent;ctx.fillRect(0,444,960,2);
    }
    for(const o of w.obstacles){
      const x=Math.round(o.x-d),h=o.height??(o.kind==='barrier'?60:40);
      if(x>1000||x+o.width<0)continue;
      if(o.kind==='gap'){
        ctx.fillStyle=art.sky;ctx.fillRect(x,444,o.width,96);ctx.fillStyle=art.accent;ctx.fillRect(x-4,444,4,22);ctx.fillRect(x+o.width,444,4,22);
      }else if(o.kind==='gate'){
        const top=o.center-o.gap/2,bottom=o.center+o.gap/2;
        ctx.fillStyle=s.theme==='forest'?'#654d48':s.theme==='ice'?'#729db5':'#435768';ctx.fillRect(x,0,o.width,top);ctx.fillRect(x,bottom,o.width,540-bottom);
        ctx.save();ctx.beginPath();ctx.rect(x,0,o.width,top);ctx.rect(x,bottom,o.width,540-bottom);ctx.clip();
        if(s.theme==='factory'||s.theme==='neon')for(let y=0;y<540;y+=36)for(let tx=x;tx<x+o.width;tx+=36)this.tile(ctx,'industrial',11,tx,y);
        else {ctx.fillStyle=s.theme==='ice'?'#c9f6f8':'#9cac85';for(let y=10;y<540;y+=28)ctx.fillRect(x+8,y,5,18);}
        ctx.restore();ctx.fillStyle=art.accent;ctx.fillRect(x,top-8,o.width,8);ctx.fillRect(x,bottom,o.width,8);
        if(s.theme==='sky'){ctx.fillStyle='#fff2bb';ctx.fillRect(x+6,top-16,o.width-12,8);ctx.fillRect(x+6,bottom+8,o.width-12,8);}
      }else{
        // Keep the entire collision rectangle readable; spikes are a serrated top
        // over a solid base, rather than a thin triangle with an invisible hitbox.
        ctx.fillStyle=s.theme==='forest'?'#705548':s.theme==='ice'?'#9ae2ef':'#b94f73';ctx.fillRect(x,444-h,o.width,h);
        ctx.save();ctx.beginPath();ctx.rect(x,444-h,o.width,h);ctx.clip();
        if(s.theme==='factory'||s.theme==='neon')for(let tx=x;tx<x+o.width;tx+=36)this.tile(ctx,'industrial',o.kind==='barrier'?6:25,tx,444-h,36,h);
        else if(s.theme==='forest')for(let tx=x+6;tx<x+o.width;tx+=12){ctx.fillStyle='#ab8b63';ctx.fillRect(tx,448-h,3,h-8);}
        ctx.restore();ctx.fillStyle=art.accent;ctx.fillRect(x,444-h,o.width,3);
        if(o.kind==='spike')for(let tx=x+2;tx<x+o.width-3;tx+=10){ctx.beginPath();ctx.moveTo(tx,450-h);ctx.lineTo(tx+4,444-h);ctx.lineTo(Math.min(tx+8,x+o.width),450-h);ctx.fill();}
        if(o.kind==='laser'){ctx.fillStyle='#fff0cc';ctx.fillRect(x+o.width/2-2,444-h,4,h);}
      }
    }
    // Lightweight deterministic motes and action trail; no particle allocations.
    for(let i=0;i<12;i++){ctx.globalAlpha=.3;ctx.fillStyle=art.accent;const x=((i*89-d*.5)%1000+1000)%1000;ctx.fillRect(x,110+(i*53%270),2,2);}ctx.globalAlpha=1;
    if(w.feedback>0){ctx.fillStyle=art.accent;ctx.globalAlpha=w.feedback*2;for(let i=1;i<5;i++)ctx.fillRect(174-i*9,w.y+8+i*3,5,3);ctx.globalAlpha=1;}
    ctx.save();ctx.translate(180,Math.round(w.y));
    if(w.state==='lost')ctx.rotate(.5);else if(s.mode==='flap')ctx.rotate(Math.max(-.35,Math.min(.7,w.vy/650)));
    if(s.player==='robot')this.tile(ctx,'characters',Math.floor(now/130)%2,-18,-18,36,36);
    else if(s.player==='cube'){ctx.fillStyle=art.accent;ctx.fillRect(-14,-14,28,28);ctx.fillStyle='#354254';ctx.fillRect(-10,-10,20,12);}
    else if(s.player==='bird'||s.mode==='flap'){
      ctx.fillStyle='#f7d98c';ctx.fillRect(-14,-10,24,22);ctx.fillRect(-8,-14,18,8);ctx.fillStyle='#e88873';const wing=w.feedback>0?-12:Math.floor(now/110)%2*8;ctx.fillRect(-14,wing,16,7);ctx.fillStyle='#fff4bd';ctx.fillRect(2,-10,10,10);ctx.fillStyle='#2b354b';ctx.fillRect(6,-8,4,4);ctx.fillStyle='#ef9963';ctx.fillRect(12,-3,7,5);
    }else{
      ctx.fillStyle='#cb8263';ctx.fillRect(-12,-8,22,20);ctx.fillRect(-8,-16,6,10);ctx.fillRect(6,-16,6,10);ctx.fillRect(-23,0,13,8);ctx.fillStyle='#f5d9b0';ctx.fillRect(-26,-2,7,8);ctx.fillRect(3,1,12,8);ctx.fillStyle='#263c48';ctx.fillRect(5,-7,4,4);const run=w.vy===0?Math.floor(now/85)%2*4:2;ctx.fillRect(-9,10,6,4+run);ctx.fillRect(5,10,6,8-run);
    }
    ctx.restore();
  }
}
