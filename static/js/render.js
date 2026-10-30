/* render.js: Canvas drawing: terrain, explored cells, route, walls, flag and player. */
function draw(){
 const cs=getComputedStyle(document.documentElement),g=n=>cs.getPropertyValue(n).trim();
 const dpr=devicePixelRatio||1,w=cv.clientWidth;if(!w)return;
 cv.width=cv.height=Math.round(w*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
 const u=w/C,cx=i=>(i%C+.5)*u,cy=i=>((i/C|0)+.5)*u;
 ctx.fillStyle=g('--panel');ctx.fillRect(0,0,w,w);
 ctx.fillStyle=g('--mud');
 for(let i=0;i<R*C;i++)if(cost[i]>1)ctx.fillRect((i%C)*u,(i/C|0)*u,u,u);
 const line=(p,col,lw,dash)=>{if(p.length<2)return;ctx.beginPath();p.forEach((i,k)=>k?ctx.lineTo(cx(i),cy(i)):ctx.moveTo(cx(i),cy(i)));ctx.strokeStyle=col;ctx.lineWidth=lw;ctx.lineCap=ctx.lineJoin='round';ctx.setLineDash(dash?[u*.3,u*.3]:[]);ctx.stroke();ctx.setLineDash([])};
 if(run){ctx.fillStyle=g('--seen');ctx.globalAlpha=.4;for(let k=0;k<shown;k++){const i=run.order[k];ctx.fillRect((i%C)*u,(i/C|0)*u,u,u)}ctx.globalAlpha=1;
  if(shown>=run.order.length)line(run.path,g('--path'),u*.3)}
 if(hint.length)line(hint,g('--path'),u*.2,true);
 ctx.strokeStyle=g('--wall');ctx.lineWidth=Math.max(1.5,u*.09);ctx.lineCap='square';ctx.beginPath();
 for(let i=0;i<R*C;i++){const x=(i%C)*u,y=(i/C|0)*u;
  if(walls[i]&N){ctx.moveTo(x,y);ctx.lineTo(x+u,y)}
  if(walls[i]&W){ctx.moveTo(x,y);ctx.lineTo(x,y+u)}
  if(walls[i]&E){ctx.moveTo(x+u,y);ctx.lineTo(x+u,y+u)}
  if(walls[i]&S){ctx.moveTo(x,y+u);ctx.lineTo(x+u,y+u)}}
 ctx.stroke();
 ctx.fillStyle=g('--path');ctx.fillRect(cx(goal)-u*.25,cy(goal)-u*.25,u*.5,u*.5);
 for(const o of others){ctx.fillStyle=o.color;ctx.beginPath();ctx.arc((o.pos%C+.5)*u,((o.pos/C|0)+.5)*u,u*.24,0,7);ctx.fill()}
 ctx.fillStyle=g('--me');ctx.beginPath();ctx.arc((px+.5)*u,(py+.5)*u,u*.28,0,7);ctx.fill();
}

