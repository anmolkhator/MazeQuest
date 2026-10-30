/* config.js: Shared setup: DOM references, constants, game state, solver list. */
const $=s=>document.querySelector(s),cv=$('#cv'),ctx=cv.getContext('2d');
const N=1,E=2,S=4,W=8,B=[N,E,S,W],O=[S,W,N,E],DR=[-1,0,1,0],DC=[0,1,0,-1];
const ALG=[['bfs','Breadth-first (BFS)'],['dfs','Depth-first (DFS)'],['dijkstra','Dijkstra'],['greedy','Greedy best-first'],['astar','A* search']];
let px=0,py=0,held=[],last=0,R,C,walls,cost,start,goal,pl,moves,spent,t0,timer,over,run=null,shown=0,hint=[];
$('#alg').innerHTML=ALG.map(a=>`<option value="${a[0]}">${a[1]}</option>`).join('');$('#alg').value='astar';
