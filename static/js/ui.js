/* ui.js: button wiring and redraw on resize or theme change. */
$('#new').onclick = newMaze;
$('#run').onclick = () => runAlg($('#alg').value);
$('#cmp').onclick = compare;
$('#hint').onclick = async () => {
 if (over || rc) return;
 try { const r = await api('/api/solve', {alg: 'astar', pos: pl}); run = null; hint = r.path.slice(0, 8); draw(); msg('The dashed line shows the next few steps on the cheapest route.'); }
 catch (e) { msg(e.message); }
};
addEventListener('resize', draw);
matchMedia('(prefers-color-scheme:dark)').addEventListener('change', draw);
