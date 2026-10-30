/* main.js: entry point. Start the movement loop and restore a logged-in session. */
requestAnimationFrame(loop); setMode('in');
api('/api/me').then(r => { if (r.user) enter(r.user); });
