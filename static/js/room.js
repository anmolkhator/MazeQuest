/* room.js: play with friends. Polls the Python server for the room, shows everyone's dot and the race results. */
let rc = null, live = false, others = [], roundSeen = 0, poll = null, syncing = false, myName = '', flags = {};
let pendingCode = (location.pathname.match(/^\/r\/([A-Za-z0-9]{5})/) || [])[1] || null;
const ferr = t => $('#ferr').textContent = t || '';
const post = (u, b) => api(u, b || {});

async function createRoom() {
 try { enterRoom((await post('/api/room/create', {size: +$('#size').value, gen: $('#gen').value, mud: $('#mud').checked})).code); }
 catch (e) { ferr(e.message); }
}
async function joinRoom(code) {
 try { enterRoom((await post('/api/room/join', {code: String(code).trim().toUpperCase()})).code); }
 catch (e) { ferr(e.message); }
}
function enterRoom(code) {
 rc = code; roundSeen = 0; live = false; others = []; flags = {}; ferr();
 $('#fhome').hidden = true; $('#froom').hidden = false; $('#rcode').textContent = code;
 $('#rlink').value = `${location.origin}/r/${code}`; history.replaceState(null, '', '/r/' + code);
 clearInterval(poll); poll = setInterval(sync, 400); sync(); msg('You are in the room. Wait for the host to start the race.');
}
async function leaveRoom(silent) {
 const c = rc; clearInterval(poll); rc = null; live = false; others = [];
 try { await post(`/api/room/${c}/leave`); } catch (e) {}
 $('#fhome').hidden = false; $('#froom').hidden = true; $('#win').hidden = true; history.replaceState(null, '', '/');
 if (!silent) newMaze();
}
function loadMaze(m) {
 R = C = m.n; walls = m.walls; cost = m.cost; start = m.start; goal = m.goal;
 pl = start; px = py = 0; moves = 0; spent = 0; over = false; run = null; hint = []; shown = 0; t0 = 0; dirs = [];
 clearInterval(timer); $('#time').textContent = '0.0 s'; stats(); draw();
}
async function sync() {
 if (!rc || syncing) return;
 syncing = true;
 try {
  const s = await post(`/api/room/${rc}/sync`, {dirs: live ? dirs : [], round: roundSeen});
  if (!rc) return;
  if (s.maze) { loadMaze(s.maze); roundSeen = s.round; live = false; flags = {}; $('#win').hidden = true; }
  const me = s.players.find(p => p.name == myName) || {};
  others = s.players.filter(p => p.name != myName).map(p => ({pos: p.pos, color: p.color}));
  if (s.state == 'playing' && s.starts_in > 0) { live = false; msg(`Get ready… ${Math.ceil(s.starts_in)}`); }
  else if (s.state == 'playing' && !live && !over && roundSeen == s.round) {
   live = true; t0 = Date.now(); timer = setInterval(() => $('#time').textContent = ((Date.now() - t0) / 1000).toFixed(1) + ' s', 100); msg('Go! First to the flag wins.');
  }
  renderRoom(s);
  if (me.done) { held = []; over = true; clearInterval(timer); }
  if (me.done && !flags.a) { flags.a = 1; showResults(s, me); }
  else if (s.state == 'done' && !flags.a && !flags.b && roundSeen == s.round) { flags.b = 1; showResults(s, me); }
  else if (s.state == 'done' && !$('#win').hidden) showResults(s, me);
  draw();
 } catch (e) { if (rc) ferr(e.message); }
 finally { syncing = false; }
}
function renderRoom(s) {
 $('#rstate').textContent = {lobby: 'waiting for players', playing: 'race in progress', done: 'race finished'}[s.state];
 $('#plist').innerHTML = s.players.map(p => `<li><span class="dot" style="background:${p.color}"></span>${p.name}${p.name == s.host ? ' (host)' : ''}${p.name == myName ? ' (you)' : ''}<span class="r">${p.done ? '#' + p.rank + ' · ' + p.time.toFixed(1) + ' s' : s.state == 'playing' ? 'racing' : 'ready'}</span></li>`).join('');
 $('#startrace').hidden = s.host != myName || s.state == 'playing';
 $('#startrace').textContent = s.state == 'lobby' ? 'Start race' : 'Rematch';
}
function showResults(s, me) {
 const ranked = s.players.filter(p => p.done).sort((a, b) => a.rank - b.rank), rest = s.players.filter(p => !p.done), w = ranked[0];
 $('#wt').textContent = me.done ? (me.rank == 1 ? 'You won the race!' : `You finished #${me.rank}`) : 'Race over';
 $('#wsub').textContent = w ? `${w.name} won in ${w.time.toFixed(1)} s` : 'Nobody reached the flag.';
 $('#wst').innerHTML = ranked.map(p => `<div class="stat"><span>#${p.rank} ${p.name}</span><b>${p.time.toFixed(1)} s · ${p.score} pts</b></div>`)
  .concat(rest.map(p => `<div class="stat"><span>${p.name}</span><b>${s.state == 'done' ? 'did not finish' : 'racing…'}</b></div>`)).join('');
 $('#win').hidden = false;
}
async function refreshInvites() {
 if (rc || $('#app').hidden) return;
 try {
  const r = await api('/api/me');
  $('#invs').innerHTML = (r.invites || []).map(i => `<div class="row" style="align-items:center"><span class="note" style="margin:0">${i.host} invited you</span><button data-c="${i.code}">Join</button></div>`).join('');
 } catch (e) {}
}
$('#mkroom').onclick = createRoom;
$('#joinroom').onclick = () => joinRoom($('#jcode').value);
$('#invs').onclick = e => { if (e.target.dataset.c) joinRoom(e.target.dataset.c); };
$('#leave').onclick = () => leaveRoom(false);
$('#startrace').onclick = async () => { try { ferr(); await post(`/api/room/${rc}/start`); sync(); } catch (e) { ferr(e.message); } };
$('#sendinv').onclick = async () => {
 try { await post(`/api/room/${rc}/invite`, {user: $('#inv').value}); ferr(''); $('#inv').value = ''; msg('Invite sent. They will see it on their screen.'); } catch (e) { ferr(e.message); }
};
$('#copy').onclick = async () => { try { await navigator.clipboard.writeText($('#rlink').value); } catch (e) { $('#rlink').select(); } msg('Invite link copied. Send it to your friends.'); };
setInterval(refreshInvites, 4000);
