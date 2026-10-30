/* input.js: Keyboard and touch controls, plus the smooth movement loop. */
const KEYS={arrowup:0,w:0,arrowright:1,d:1,arrowdown:2,s:2,arrowleft:3,a:3};
addEventListener('keydown',e=>{
 const d=KEYS[e.key.toLowerCase()];
 if(d===undefined||/SELECT|INPUT/.test(document.activeElement.tagName))return;
 e.preventDefault();if(!held.includes(d))held.push(d);
});
addEventListener('keyup',e=>{const d=KEYS[e.key.toLowerCase()];held=held.filter(x=>x!==d)});
addEventListener('blur',()=>held=[]);
/* Smooth movement: the logical cell updates at once, the drawn dot glides toward it */
function loop(ts){
 if(!R){requestAnimationFrame(loop);return}
 const dt=Math.min(.05,(ts-last)/1000||0);last=ts;
 const tgx=pl%C,tgy=pl/C|0,dx=tgx-px,dy=tgy-py,dist=Math.hypot(dx,dy);
 if(dist>.001){const s=Math.min(dist,(cost[pl]>1?7:16)*dt);px+=dx/dist*s;py+=dy/dist*s;draw()}
 else{px=tgx;py=tgy;if(held.length)move(held[held.length-1])}
 requestAnimationFrame(loop);
}
let tx,ty;
cv.addEventListener('touchstart',e=>{tx=e.touches[0].clientX;ty=e.touches[0].clientY},{passive:true});
cv.addEventListener('touchmove',e=>{
 const dx=e.touches[0].clientX-tx,dy=e.touches[0].clientY-ty;
 if(Math.max(Math.abs(dx),Math.abs(dy))<15){held=[];return}
 held=[Math.abs(dx)>Math.abs(dy)?(dx>0?1:3):(dy>0?2:0)];
},{passive:true});
cv.addEventListener('touchend',()=>held=[]);
