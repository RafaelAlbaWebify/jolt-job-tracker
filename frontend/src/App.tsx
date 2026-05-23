import { useEffect, useMemo, useState } from 'react';
import { fetchBackendHealth, type HealthResponse } from './api';

type PageId = 'capture' | 'review' | 'profiles' | 'history' | 'manual' | 'about';

type Page = {
  id: PageId;
  label: string;
  eyebrow: string;
  title: string;
  body: string;
};

const pages: Page[] = [
  {
    id: 'capture',
    label: 'Capture',
    eyebrow: 'Primary workflow',
    title: 'Capture jobs',
    body:
      'Capture will become the main entry point for browser-assisted job collection. Real capture, parsing, sorting, and export logic are intentionally not implemented in this skeleton.',
  },
  {
    id: 'review',
    label: 'Review Dashboard',
    eyebrow: 'After capture',
    title: 'Review dashboard',
    body:
      'This view will summarize captured, parsed, Apply, Maybe, Manual Review, Discard, Duplicate, and Already Reviewed jobs before export.',
  },
  {
    id: 'profiles',
    label: 'Rule Profiles',
    eyebrow: 'Configuration',
    title: 'Rule profiles',
    body:
      'Profiles will make filtering reusable and portfolio-safe. Profile loading and editing are deferred to a later phase.',
  },
  {
    id: 'history',
    label: 'History / Tracker',
    eyebrow: 'Application status',
    title: 'History and tracker',
    body:
      'This section will track application statuses and already-reviewed jobs. Persistence and exports are not part of this skeleton.',
  },
  {
    id: 'manual',
    label: 'Manual Paste / Debug',
    eyebrow: 'Secondary fallback',
    title: 'Manual paste and parser debug',
    body:
      'Manual paste is reserved for one-off review, parser testing, demos without capture, and recovery when capture fails. It is not the primary workflow.',
  },
  {
    id: 'about',
    label: 'About',
    eyebrow: 'Local assistant',
    title: 'About LinkAut',
    body:
      'LinkAut is a local job-offer automation assistant for capture, parsing, configurable sorting, human review, and tracker-ready exports.',
  },
];

function App() {
  const [activePageId, setActivePageId] = useState<PageId>('capture');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const activePage = useMemo(
    () => pages.find((page) => page.id === activePageId) ?? pages[0],
    [activePageId],
  );

  useEffect(() => {
    let cancelled = false;

    fetchBackendHealth()
      .then((result) => {
        if (!cancelled) {
          setHealth(result);
          setHealthError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setHealth(null);
          setHealthError(error instanceof Error ? error.message : 'Backend unavailable');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand">
          <span className="brand-mark">LA</span>
          <div>
            <strong>LinkAut</strong>
            <span>Local job assistant</span>
          </div>
        </div>

        <nav className="nav-list">
          {pages.map((page) => (
            <button
              key={page.id}
              className={page.id === activePageId ? 'nav-item active' : 'nav-item'}
              type="button"
              onClick={() => setActivePageId(page.id)}
            >
              {page.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">{activePage.eyebrow}</p>
            <h1>{activePage.title}</h1>
          </div>
          <div className={health ? 'health-pill ok' : 'health-pill warn'}>
            <span>{health ? 'Backend online' : 'Backend offline'}</span>
            <small>{health?.message ?? healthError ?? 'Checking /api/health'}</small>
          </div>
        </header>

        <section className="content-panel">
          <p>{activePage.body}</p>

          {activePage.id === 'capture' ? (
            <div className="placeholder-grid" aria-label="Capture workflow placeholders">
              <div>
                <span>1</span>
                <strong>Select profile</strong>
                <p>Profile loading arrives in a later phase.</p>
              </div>
              <div>
                <span>2</span>
                <strong>Capture jobs</strong>
                <p>Browser-assisted capture is not wired yet.</p>
              </div>
              <div>
                <span>3</span>
                <strong>Review before export</strong>
                <p>Parsing, sorting, and exports are deferred.</p>
              </div>
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}

export default App;
