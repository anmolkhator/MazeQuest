/* analysis.js: the solver panel. The algorithms run in Python on the server. */
async function runAlg(a) {
 if (over || rc) return;
 let r;
 try { r = await api('/api/solve', {alg: a, pos: pl}); } catch (e) { return msg(e.message); }
 run = r; shown = 0; hint = [];
 $('#res').textContent = `${ALG.find(x => x[0] == a)[1]}: explored ${r.order.length} cells, route of ${r.steps} steps, cost ${r.cost}, ${r.ms.toFixed(2)} ms (Python).`;
 (function tick() {
  if (run !== r) return;
  shown = Math.min(r.order.length, shown + Math.max(1, Math.ceil(r.order.length / 80))); draw();
  if (shown < r.order.length) requestAnimationFrame(tick);
 })();
}
async function compare() {
 if (over || rc) return;
 let rows;
 try { rows = await api('/api/compare', {pos: pl}); } catch (e) { return msg(e.message); }
 const best = Math.min(...rows.map(r => r.cost));
 $('#tbl').innerHTML = '<tr><th>Algorithm</th><th>Explored</th><th>Steps</th><th>Cost</th><th>ms</th></tr>' +
  rows.map(r => `<tr class="${r.cost == best ? 'best' : ''}"><td>${r.name}</td><td>${r.explored}</td><td>${r.steps}</td><td>${r.cost}</td><td>${r.ms.toFixed(2)}</td></tr>`).join('');
 $('#res').textContent = 'Highlighted rows found the cheapest route (computed by Python).';
}
