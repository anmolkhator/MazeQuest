/* graph.js: Maze as a graph: every cell is a vertex, every missing wall is an edge. Helpers to move between cells and carve walls. */
const rnd=n=>Math.random()*n|0;
const shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=rnd(i+1);[a[i],a[j]]=[a[j],a[i]]}return a};
const step=(i,d)=>i+DR[d]*C+DC[d];
const inb=(i,d)=>{const r=(i/C|0)+DR[d],c=i%C+DC[d];return r>=0&&r<R&&c>=0&&c<C};
const carve=(i,d)=>{const j=step(i,d);walls[i]&=~B[d];walls[j]&=~O[d]};
const nb=i=>{const o=[];for(let d=0;d<4;d++)if(!(walls[i]&B[d])&&inb(i,d))o.push(step(i,d));return o};
