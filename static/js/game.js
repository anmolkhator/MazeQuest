/* game.js: asks the Python server for mazes, handles the player's moves locally, reports the finish. */
const api = async (url, body) => {
 const r = await fetch(url, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
 const j = await r.json().catch(() => ({}));
 if (!r.ok) throw new Error(j.error || 'Server error ' + r.status);
 return j;
};
let dirs = [];
const msg = t => $('#msg').textContent = t;
const stats = () => {$('#mv').textContent = moves; $('#cost').textContent = spent};

async function newMaze() {
 if (rc) return;
 let m;
 try { m = await api(`/api/maze?size=${$('#size').value}&gen=${$('#gen').value}&loops=${$('#loops').value}&mud=${$('#mud').checked ? 1 : 0}`); }
 catch (e) { return msg(e.message); }
 R = C = m.n; walls = m.walls; cost = m.cost; start = m.start; goal = m.goal;
 pl = start; px = py = 0; moves = 0; spent = 0; over = false; run = null; hint = []; shown = 0; t0 = 0; dirs = [];
 clearInterval(timer);
 $('#time').textContent = '0.0 s'; $('#tbl').innerHTML = ''; $('#res').textContent = 'Pick an algorithm and run it, or compare all five at once.';
 stats(); msg('Reach the flag in the bottom-right corner. Hold arrow keys or WASD, or drag on the board.'); draw();
}

function move(d) {
 if (over || (rc && !live) || walls[pl] & B[d] || !inb(pl, d)) return;
 if (!t0) { t0 = Date.now(); timer = setInterval(() => $('#time').textContent = ((Date.now() - t0) / 1000).toFixed(1) + ' s', 100); }
 pl = step(pl, d); moves++; spent += cost[pl]; dirs.push(d); hint = []; run = null; stats();
 if (pl == goal) finish();
 draw();
}

async function finish() {
 over = true; clearInterval(timer); held = [];
 if (rc) return;
 let r;
 try { r = await api('/api/finish', {dirs, seconds: (Date.now() - t0) / 1000}); }
 catch (e) { return msg('Could not save your score: ' + e.message); }
 msg(`You won! Score ${r.score}.`); loadProfile();
 setTimeout(() => {
  $('#wt').textContent = `${$('#uname').textContent} won!`;
  $('#wsub').textContent = r.pb ? 'New personal best!' : (r.eff == 100 ? 'A perfect, optimal route.' : 'You reached the flag.');
  $('#wst').innerHTML = [['Score', r.score], ['Moves', r.moves], ['Path cost', `${r.cost} (best ${r.best})`], ['Efficiency', r.eff + '%'], ['Time', r.sec.toFixed(1) + ' s']]
   .map(x => `<div class="stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
  $('#win').hidden = false;
 }, 450);
}
