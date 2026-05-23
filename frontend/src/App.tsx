import { useEffect, useMemo, useState } from 'react';
import {
  fetchBackendHealth,
  fetchProfile,
  fetchProfiles,
  type HealthResponse,
  type RuleProfile,
  type RuleProfileSummary,
} from './api';

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
      'Profiles make LinkAut reusable. Select a default profile to inspect its rules; editing and classification arrive in later phases.',
  },
  {
    id: 'history',
    label: 'History / Tracker',
    eyebrow: 'Application status',
    title: 'History and tracker',
    body:
      'This section will track application statuses and already-reviewed jobs. Persistence and exports are not part of this phase.',
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

function joinValues(values: string[]): string {
  return values.length > 0 ? values.join(', ') : 'None configured';
}

function App() {
  const [activePageId, setActivePageId] = useState<PageId>('capture');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<RuleProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');
  const [selectedProfile, setSelectedProfile] = useState<RuleProfile | null>(null);
  const [profilesError, setProfilesError] = useState<string | null>(null);
  const [profilesLoading, setProfilesLoading] = useState<boolean>(true);

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

  useEffect(() => {
    let cancelled = false;

    setProfilesLoading(true);
    fetchProfiles()
      .then((result) => {
        if (!cancelled) {
          setProfiles(result);
          setProfilesError(null);
          setSelectedProfileId(
            result.find((profile) => profile.profile_id === 'rafael_default')?.profile_id ??
              result[0]?.profile_id ??
              '',
          );
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setProfiles([]);
          setProfilesError(error instanceof Error ? error.message : 'Unable to load profiles');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setProfilesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedProfileId) {
      setSelectedProfile(null);
      return;
    }

    let cancelled = false;

    fetchProfile(selectedProfileId)
      .then((result) => {
        if (!cancelled) {
          setSelectedProfile(result);
          setProfilesError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setSelectedProfile(null);
          setProfilesError(error instanceof Error ? error.message : 'Unable to load profile detail');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProfileId]);

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
                <p>Profile selection is available on the Rule Profiles page.</p>
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

          {activePage.id === 'profiles' ? (
            <div className="profiles-layout">
              {profilesError ? <p className="status-message">{profilesError}</p> : null}
              {profilesLoading ? <p className="status-message">Loading profiles...</p> : null}

              <div className="profile-list" aria-label="Available rule profiles">
                {profiles.map((profile) => (
                  <button
                    key={profile.profile_id}
                    className={
                      profile.profile_id === selectedProfileId ? 'profile-option active' : 'profile-option'
                    }
                    type="button"
                    onClick={() => setSelectedProfileId(profile.profile_id)}
                  >
                    <strong>{profile.display_name}</strong>
                    <span>{profile.description}</span>
                  </button>
                ))}
              </div>

              {selectedProfile ? (
                <article className="profile-detail">
                  <div className="profile-detail-header">
                    <div>
                      <h2>{selectedProfile.display_name}</h2>
                      <p>{selectedProfile.description}</p>
                    </div>
                    <span className="profile-badge">
                      {selectedProfile.profile_id === 'rafael_default'
                        ? 'Demo/default preset'
                        : 'Reusable preset'}
                    </span>
                  </div>

                  {selectedProfile.profile_id === 'rafael_default' ? (
                    <p className="profile-note">
                      Rafael Default is one editable demo/default profile. It is not a global hardcoded
                      rule set for every user.
                    </p>
                  ) : null}

                  <dl className="profile-fields">
                    <div>
                      <dt>Accepted languages</dt>
                      <dd>{joinValues(selectedProfile.accepted_languages)}</dd>
                    </div>
                    <div>
                      <dt>Mandatory language mode</dt>
                      <dd>{selectedProfile.mandatory_language_mode}</dd>
                    </div>
                    <div>
                      <dt>Base location</dt>
                      <dd>{selectedProfile.base_location}</dd>
                    </div>
                    <div>
                      <dt>Max hybrid/onsite distance</dt>
                      <dd>{selectedProfile.max_distance_km_for_hybrid_onsite} km</dd>
                    </div>
                    <div>
                      <dt>Remote ignores distance</dt>
                      <dd>{selectedProfile.remote_ignores_distance ? 'Yes' : 'No'}</dd>
                    </div>
                    <div>
                      <dt>Preferred work modes</dt>
                      <dd>{joinValues(selectedProfile.preferred_work_modes)}</dd>
                    </div>
                    <div>
                      <dt>Acceptable work modes</dt>
                      <dd>{joinValues(selectedProfile.acceptable_work_modes)}</dd>
                    </div>
                    <div>
                      <dt>Portfolio safe</dt>
                      <dd>{selectedProfile.portfolio_safe ? 'Yes' : 'No'}</dd>
                    </div>
                  </dl>

                  <div className="keyword-sections">
                    <section>
                      <h3>Positive keywords</h3>
                      <p>{joinValues(selectedProfile.positive_keywords)}</p>
                    </section>
                    <section>
                      <h3>Risk keywords</h3>
                      <p>{joinValues(selectedProfile.risk_keywords)}</p>
                    </section>
                    <section>
                      <h3>Discard keywords</h3>
                      <p>{joinValues(selectedProfile.discard_keywords)}</p>
                    </section>
                    <section>
                      <h3>Stretch skills</h3>
                      <p>{joinValues(selectedProfile.stretch_skills)}</p>
                    </section>
                  </div>

                  <section className="severity-list">
                    <h3>Risk severity settings</h3>
                    <dl>
                      {Object.entries(selectedProfile.risk_severity_settings).map(([risk, severity]) => (
                        <div key={risk}>
                          <dt>{risk}</dt>
                          <dd>{severity}</dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                </article>
              ) : null}
            </div>
          ) : null}
        </section>
      </main>
    </div>
  );
}

export default App;
