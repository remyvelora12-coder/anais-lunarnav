import { useState } from 'react';

type Site = { latitude_deg: number; longitude_deg: number; observer_height_m: number };
type Geometry = { azimuth_deg: number | null; elevation_deg: number; range_km: number; visible_geometric_center: boolean };
type Summary = {
  sample_count: number; known_sample_count: number; unknown_sample_count: number;
  visible_sample_count: number; visible_sample_fraction: number | null;
  continuous_visibility_duration_seconds: null;
  transition_brackets: Array<{ start_utc: string; end_utc: string; from_visible: boolean; to_visible: boolean }>;
  sampling_notice: string;
};
type SiteOutput = {
  snapshots: Array<{ utc: string; sun: Geometry; earth: Geometry }>;
  solar_summary: Summary; earth_summary: Summary;
};
type Result = {
  calculation_status: 'EXECUTED'; reference_frame: string; model: string;
  start_utc: string; end_utc: string; sample_interval_seconds: number;
  sites: { alpha: SiteOutput; bravo: SiteOutput };
  provenance: { spiceypy_version: string; kernels: Array<{ filename: string; sha256: string }> };
  warnings: string[];
};
type FormSite = { lat: string; lon: string; height: string };
type Form = { alpha: FormSite; bravo: FormSite; start: string; end: string; step: string };
const INITIAL: Form = {
  alpha: { lat: '-89.5', lon: '0', height: '2' },
  bravo: { lat: '-88.5', lon: '45', height: '2' },
  start: '2026-11-14T00:00', end: '2026-11-15T00:00', step: '3600',
};
const API = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

function utc(value: string): string {
  // Input type=datetime-local has no timezone: interface convention is explicitly UTC.
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(value)) throw Error('Choose valid UTC start and end timestamps.');
  return value + ':00Z';
}
function site(input: FormSite): Site {
  for (const item of [input.lat, input.lon, input.height]) {
    if (item.trim() === '' || !Number.isFinite(Number(item))) throw Error('Each coordinate and height must be a finite number.');
  }
  return { latitude_deg: Number(input.lat), longitude_deg: Number(input.lon), observer_height_m: Number(input.height) };
}
function display(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? 'UNKNOWN' : value.toFixed(digits);
}
function summaryCard(name: string, data: SiteOutput) {
  return (
    <article className="site-card">
      <h3>{name}</h3>
      {(['solar_summary', 'earth_summary'] as const).map((key) => {
        const v = data[key];
        return <section key={key} className="metric">
          <div className="metric-title">{key === 'solar_summary' ? 'Sun' : 'Earth'}</div>
          <strong>{v.visible_sample_count} / {v.known_sample_count} visible samples</strong>
          <p>{v.unknown_sample_count} unknown samples · {v.transition_brackets.length} detected transition brackets</p>
          <span>{v.sampling_notice}</span>
        </section>;
      })}
    </article>
  );
}

export default function App() {
  const [form, setForm] = useState<Form>(INITIAL);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<'unknown' | 'ok' | 'unavailable'>('unknown');
  const update = (name: 'alpha' | 'bravo', field: keyof FormSite, value: string) =>
    setForm((current) => ({ ...current, [name]: { ...current[name], [field]: value } }));
  async function checkHealth() {
    try {
      const response = await fetch(API + '/health');
      if (!response.ok) throw Error('Service unavailable');
      const body = await response.json() as { status: string };
      setHealth(body.status === 'ok' ? 'ok' : 'unavailable');
    } catch { setHealth('unavailable'); }
  }
  async function execute(event: React.FormEvent) {
    event.preventDefault(); setError(''); setResult(null); setLoading(true);
    try {
      const payload = {
        site_alpha: site(form.alpha), site_bravo: site(form.bravo),
        start_utc: utc(form.start), end_utc: utc(form.end),
        sample_interval_seconds: Number(form.step), reference_frame: 'IAU_MOON',
      };
      const response = await fetch(API + '/v1/analysis/compare-window', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json() as Result & { detail?: unknown };
      if (!response.ok) {
        throw Error(typeof data.detail === 'object' ? JSON.stringify(data.detail) : 'Scientific service returned an error.');
      }
      setResult(data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unknown analysis error'); }
    finally { setLoading(false); }
  }
  function exportJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = href; a.download = 'anais-lunarnav-analysis.json'; a.click();
    URL.revokeObjectURL(href);
  }
  return <div className="shell">
    <header><span className="eyebrow">ANAIS LunarLink™ / Scientific Research</span>
      <h1>LunarNav™ Mission Control</h1>
      <p>Compare lunar Sun and Earth visibility at two locations using actual SPICE-backed snapshots. Terrain and landing safety are not validated.</p>
    </header>
    <main>
      <section className="panel" aria-labelledby="config"><div className="section-top"><h2 id="config">Mission configuration</h2>
        <button type="button" className="secondary" onClick={checkHealth}>Check backend health</button></div>
        <p className="muted">Backend status: {health.toUpperCase()} · Reference frame: IAU_MOON · Mean-sphere geometric model</p>
        <form onSubmit={execute}>
          <div className="columns">{(['alpha','bravo'] as const).map((name) => <fieldset key={name}>
            <legend>Site {name.toUpperCase()}</legend>
            {([['lat','Latitude (°)'],['lon','East longitude (°)'],['height','Height above mean sphere (m)']] as const).map(([field,label]) =>
              <label key={field}>{label}<input type="number" step="any" required value={form[name][field]} onChange={(e) => update(name,field,e.target.value)} /></label>)}
          </fieldset>)}</div>
          <div className="columns">
            <label>Start time (UTC)<input type="datetime-local" value={form.start} required onChange={(e) => setForm({ ...form, start: e.target.value })} /></label>
            <label>End time (UTC)<input type="datetime-local" value={form.end} required onChange={(e) => setForm({ ...form, end: e.target.value })} /></label>
          </div>
          <label>Sampling interval<select value={form.step} onChange={(e) => setForm({ ...form, step: e.target.value })}>
            <option value="900">15 minutes</option><option value="1800">30 minutes</option>
            <option value="3600">1 hour</option><option value="7200">2 hours</option><option value="21600">6 hours</option>
          </select></label>
          <button type="submit" disabled={loading}>{loading ? 'Analyzing…' : 'Run scientific comparison'}</button>
          {error && <div role="alert" className="error"><strong>Analysis unavailable</strong><p>{error}</p><p>Check backend availability, configured SPICE kernels, timestamps and coverage.</p></div>}
        </form>
      </section>
      {result && <section className="panel" aria-label="Scientific results" aria-live="polite">
        <div className="section-top"><h2>Comparison results</h2><button type="button" className="secondary" onClick={exportJson}>Export evidence JSON</button></div>
        <p className="muted">Model: {result.model} · Sampled from {result.start_utc} to {result.end_utc}</p>
        <div className="columns">{summaryCard('Site Alpha',result.sites.alpha)}{summaryCard('Site Bravo',result.sites.bravo)}</div>
        <h3>Snapshot table — Site Alpha</h3>
        <div className="table-scroll"><table><thead><tr><th>UTC</th><th>Sun elevation (°)</th><th>Sun visible</th><th>Earth elevation (°)</th><th>Earth visible</th></tr></thead><tbody>
          {result.sites.alpha.snapshots.map((row) => <tr key={row.utc}><td>{row.utc}</td><td>{display(row.sun.elevation_deg)}</td><td>{String(row.sun.visible_geometric_center)}</td><td>{display(row.earth.elevation_deg)}</td><td>{String(row.earth.visible_geometric_center)}</td></tr>)}
        </tbody></table></div>
        <h3>Kernel provenance</h3><p>SpiceyPy {result.provenance.spiceypy_version}</p>
        <div className="hashes">{result.provenance.kernels.map((k) => <p key={k.sha256}><strong>{k.filename}</strong> · SHA-256 <code>{k.sha256}</code></p>)}</div>
        <h3>Scientific warnings</h3><ul>{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
      </section>}
      <aside className="disclaimer">Research prototype. Snapshot fractions are not visibility-duration fractions. No terrain obstruction, landing-site safety certification, or operational navigation claims.</aside>
    </main>
    <footer>Property of Aegis Air Intelligence Systems LLC &amp; ANAIS Technology LLC · Prepared under the direction of Edward Guillen Morejon, Founder &amp; CEO · © 2025 Aegis Air Intelligence Systems LLC &amp; ANAIS Technology LLC. All Rights Reserved.</footer>
  </div>;
}
