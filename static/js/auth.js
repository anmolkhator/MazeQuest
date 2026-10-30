/* auth.js: sign up, log in, log out and the profile/leaderboard. Accounts live in the Python server's SQLite database. */
let mode = 'in';
function setMode(m) {
 mode = m; $('#tin').classList.toggle('on', m == 'in'); $('#tup').classList.toggle('on', m == 'up');
 $('#go').textContent = m == 'in' ? 'Log in' : 'Create account'; $('#aerr').textContent = '';
}
$('#tin').onclick = () => setMode('in'); $('#tup').onclick = () => setMode('up');
$('#af').onsubmit = async e => {
 e.preventDefault();
 try { const r = await api('/api/' + (mode == 'up' ? 'register' : 'login'), {user: $('#au').value.trim(), pw: $('#ap').value}); enter(r.user); }
 catch (err) { $('#aerr').textContent = err.message; }
};
function enter(u) {
 myName = u;
 $('#au').value = $('#ap').value = ''; $('#auth').hidden = true; $('#app').hidden = false;
 $('#uname').textContent = u; $('#hi').textContent = `Welcome, ${u}`; newMaze(); loadProfile();
 if (pendingCode) { const c = pendingCode; pendingCode = null; joinRoom(c); }
}
async function out() {
 if (rc) await leaveRoom(true);
 await api('/api/logout', {}); held = []; clearInterval(timer); R = 0;
 $('#win').hidden = true; $('#app').hidden = true; $('#auth').hidden = false;
}
async function loadProfile() {
 const r = await api('/api/me'); if (!r.user) return;
 $('#prof').textContent = `Your wins: ${r.wins} · Best score: ${r.best}`;
 $('#lb').innerHTML = r.board.length ? r.board.map(b => `<li><b>${b.user}</b>: ${b.score} pts (${b.size}×${b.size}, ${b.eff}% efficient)</li>`).join('') : '<li>No wins yet. Be the first.</li>';
}
$('#logout').onclick = out; $('#wout').onclick = out;
$('#again').onclick = () => { $('#win').hidden = true; if (!rc) newMaze(); };
