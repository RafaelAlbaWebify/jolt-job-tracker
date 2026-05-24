import { useEffect, useMemo, useState } from 'react';
import {
  exportCaptureResult,
  fetchBackendHealth,
  fetchCaptureHealth,
  fetchProfile,
  fetchProfiles,
  runCaptureReview,
  type CaptureHealthStatus,
  type CaptureJobResult,
  type CaptureRunResult,
  type DecisionResult,
  type ExportCaptureResultResponse,
  type ExportFormat,
  type HealthResponse,
  type NormalizedJob,
  type RuleProfile,
  type RuleProfileSummary,
} from './api';

type PageId = 'capture' | 'review' | 'profiles' | 'history' | 'manual' | 'about';
type DecisionFilter = 'All' | 'Apply' | 'Maybe' | 'Discard' | 'Manual Review' | 'Duplicate' | 'Errors';
type DecisionCountKey = DecisionFilter | 'Errors';

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
      'Run a simulated capture review from manually staged raw job text. The backend still uses the real parser, profile, and decision engine chain.',
  },
  {
    id: 'review',
    label: 'Review Dashboard',
    eyebrow: 'After capture',
    title: 'Review dashboard',
    body:
      'Capture run results now appear on the Capture page after a simulated run. Persistent queues and editable statuses arrive in later phases.',
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

const decisionFilters: DecisionFilter[] = [
  'All',
  'Apply',
  'Maybe',
  'Discard',
  'Manual Review',
  'Duplicate',
  'Errors',
];

const demoJobs = [
  `Title: Microsoft 365 Technical Support Specialist
Company: Northstar SaaS
Location: Remote, Spain
Work mode: Remote
English required. Spanish is a plus.
We need a Technical Support specialist for Microsoft 365, Entra ID, endpoint troubleshooting, networking basics, and SaaS support. Stable daytime schedule with automation-adjacent support work.`,
  `Title: IT Support Engineer
Company: Alpen Desk
Location: Remote, Spain
Work mode: Remote
German required. English preferred.
Support Windows endpoints, tickets, identity access, and Microsoft 365 for business users.`,
  `Title: Infrastructure Support Technician
Company: Metro Systems
Location: Madrid, Spain
Work mode: Hybrid
English required. Onsite presence in Madrid three days per week. Support endpoint, networking, and infrastructure operations.`,
  `Support role.
Company unknown.
Tickets and users.
Need help soon.`,
];

function joinValues(values: string[] | undefined): string {
  return values && values.length > 0 ? values.join(', ') : 'None';
}

function decisionClass(decision: string | undefined): string {
  return `decision-badge decision-${(decision ?? 'unknown').toLowerCase().replace(/\s+/g, '-')}`;
}

function hasErrors(result: CaptureJobResult): boolean {
  return result.errors.length > 0;
}

function buildDecisionCounts(results: CaptureJobResult[]): Record<DecisionCountKey, number> {
  return results.reduce<Record<DecisionCountKey, number>>(
    (counts, result) => {
      counts.All += 1;
      if (hasErrors(result)) {
        counts.Errors += 1;
      }

      const decision = result.decision?.decision;
      if (decision && decision in counts) {
        counts[decision as DecisionFilter] += 1;
      }

      return counts;
    },
    {
      All: 0,
      Apply: 0,
      Maybe: 0,
      Discard: 0,
      'Manual Review': 0,
      Duplicate: 0,
      Errors: 0,
    },
  );
}

function SummaryMetric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="summary-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CompactList({ items }: { items: string[] | undefined }) {
  if (!items || items.length === 0) {
    return <p className="muted-text">None</p>;
  }

  return (
    <ul>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function TextList({ title, items }: { title: string; items: string[] | undefined }) {
  return (
    <section className="text-list">
      <h4>{title}</h4>
      <CompactList items={items} />
    </section>
  );
}

function DetailSection({ title, items }: { title: string; items: string[] | undefined }) {
  const count = items?.length ?? 0;

  return (
    <details className="detail-section">
      <summary>
        <span>{title}</span>
        <strong>{count}</strong>
      </summary>
      <CompactList items={items} />
    </details>
  );
}

function JobFacts({ job }: { job: NormalizedJob | null }) {
  return (
    <dl className="job-facts">
      <div>
        <dt>Location</dt>
        <dd>{job?.location || 'Unknown location'}</dd>
      </div>
      <div>
        <dt>Work mode</dt>
        <dd>{job?.work_mode || 'unknown'}</dd>
      </div>
      <div>
        <dt>Parser confidence</dt>
        <dd>{job?.parser_confidence || 'unknown'}</dd>
      </div>
    </dl>
  );
}

function DecisionCard({ result, index }: { result: CaptureJobResult; index: number }) {
  const job = result.parsed_job;
  const decision: DecisionResult | null = result.decision;
  const rawPreview = result.raw_job.raw_text.slice(0, 360);

  return (
    <article className="decision-card">
      <div className="decision-card-header">
        <div>
          <div className="decision-title-row">
            <span className={decisionClass(decision?.decision)}>{decision?.decision ?? 'Error'}</span>
            <span className="confidence-pill">{job?.parser_confidence ?? 'unknown confidence'}</span>
          </div>
          <h3>{job?.title || `Raw job ${index + 1}`}</h3>
          <p>
            {job?.company || 'No company parsed yet'}
            {job?.source_url ? (
              <>
                {' '}
                <a href={job.source_url} target="_blank" rel="noreferrer">
                  Source
                </a>
              </>
            ) : null}
          </p>
        </div>
        <div className="score-block">
          <span>{decision?.priority ?? 'No priority'}</span>
          <strong>{decision ? decision.score : 'N/A'}</strong>
        </div>
      </div>

      <JobFacts job={job} />

      <div className="card-section-grid">
        <TextList title="Reasons" items={decision?.reasons} />
        {result.errors.length > 0 ? <TextList title="Errors" items={result.errors} /> : null}
      </div>

      <div className="detail-grid">
        <DetailSection title="Warnings" items={decision?.warnings} />
        <DetailSection title="Missing information" items={decision?.missing_information} />
        <DetailSection title="Matched positive keywords" items={decision?.matched_positive_keywords} />
        <DetailSection title="Matched risk keywords" items={decision?.matched_risk_keywords} />
        <details className="detail-section">
          <summary>
            <span>Raw staged preview</span>
            <strong>{result.raw_job.raw_text.length}</strong>
          </summary>
          <p className="raw-preview">
            {rawPreview}
            {result.raw_job.raw_text.length > rawPreview.length ? '...' : ''}
          </p>
        </details>
      </div>
    </article>
  );
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
  const [captureHealth, setCaptureHealth] = useState<CaptureHealthStatus | null>(null);
  const [captureHealthError, setCaptureHealthError] = useState<string | null>(null);
  const [rawJobText, setRawJobText] = useState<string>('');
  const [stagedJobs, setStagedJobs] = useState<string[]>([]);
  const [captureResult, setCaptureResult] = useState<CaptureRunResult | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [captureLoading, setCaptureLoading] = useState<boolean>(false);
  const [activeFilter, setActiveFilter] = useState<DecisionFilter>('All');
  const [includeRawTextInExport, setIncludeRawTextInExport] = useState<boolean>(false);
  const [exportLoading, setExportLoading] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportResponses, setExportResponses] = useState<ExportCaptureResultResponse[]>([]);

  const activePage = useMemo(
    () => pages.find((page) => page.id === activePageId) ?? pages[0],
    [activePageId],
  );

  const filteredResults = useMemo(() => {
    if (!captureResult) {
      return [];
    }

    if (activeFilter === 'All') {
      return captureResult.results;
    }

    if (activeFilter === 'Errors') {
      return captureResult.results.filter(hasErrors);
    }

    return captureResult.results.filter((result) => result.decision?.decision === activeFilter);
  }, [activeFilter, captureResult]);

  const decisionCounts = useMemo(
    () => buildDecisionCounts(captureResult?.results ?? []),
    [captureResult],
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

    fetchCaptureHealth()
      .then((result) => {
        if (!cancelled) {
          setCaptureHealth(result);
          setCaptureHealthError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setCaptureHealth(null);
          setCaptureHealthError(error instanceof Error ? error.message : 'Capture health unavailable');
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

  function addJob() {
    const trimmed = rawJobText.trim();
    if (!trimmed) {
      setCaptureError('Paste raw job text before adding it to the staged run.');
      return;
    }

    setStagedJobs((current) => [...current, trimmed]);
    setRawJobText('');
    setCaptureError(null);
  }

  function loadDemoJobs() {
    setStagedJobs(demoJobs);
    setCaptureResult(null);
    setExportResponses([]);
    setActiveFilter('All');
    setCaptureError(null);
    setExportError(null);
  }

  function removeStagedJob(indexToRemove: number) {
    setStagedJobs((current) => current.filter((_, index) => index !== indexToRemove));
  }

  async function runReview() {
    if (!selectedProfileId) {
      setCaptureError('Select a rule profile before running capture review.');
      return;
    }

    setCaptureLoading(true);
    setCaptureError(null);

    try {
      const result = await runCaptureReview({
        profile_id: selectedProfileId,
        source: 'manual_frontend',
        dry_run: true,
        max_results: stagedJobs.length || 25,
        raw_jobs: stagedJobs.map((rawText, index) => ({
          source: 'manual_frontend',
          raw_text: rawText,
          external_id: `frontend_staged_${index + 1}`,
          capture_notes: ['Staged from the Phase 6A frontend review dashboard.'],
        })),
      });
      setCaptureResult(result);
      setCaptureHealth(result.capture_health);
      setExportResponses([]);
      setExportError(null);
      setActiveFilter('All');
    } catch (error: unknown) {
      setCaptureResult(null);
      setCaptureError(error instanceof Error ? error.message : 'Capture review failed');
    } finally {
      setCaptureLoading(false);
    }
  }

  async function runExport(exportFormat: ExportFormat) {
    if (!captureResult) {
      setExportError('Run capture review before exporting results.');
      return;
    }

    setExportLoading(exportFormat);
    setExportError(null);

    try {
      const result = await exportCaptureResult({
        export_format: exportFormat,
        include_raw_text: includeRawTextInExport,
        capture_result: captureResult,
      });
      setExportResponses((current) => [result, ...current]);
    } catch (error: unknown) {
      setExportError(error instanceof Error ? error.message : 'Export failed');
    } finally {
      setExportLoading(null);
    }
  }

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
            <div className="capture-workspace">
              <div className="capture-controls">
                <section className="control-section demo-note">
                  <div className="section-heading">
                    <h2>Demo workflow</h2>
                    <span>Safe boundary</span>
                  </div>
                  <p>
                    Browser automation is intentionally disabled here. This screen stages raw jobs,
                    then sends them through the real backend parser and decision engine.
                  </p>
                </section>

                <section className="control-section">
                  <div className="section-heading">
                    <h2>Profile</h2>
                    <span>{profilesLoading ? 'Loading' : `${profiles.length} available`}</span>
                  </div>
                  {profilesError ? <p className="status-message">{profilesError}</p> : null}
                  <label className="field-label" htmlFor="capture-profile">
                    Active rule profile
                  </label>
                  <select
                    id="capture-profile"
                    value={selectedProfileId}
                    onChange={(event) => setSelectedProfileId(event.target.value)}
                  >
                    {profiles.map((profile) => (
                      <option key={profile.profile_id} value={profile.profile_id}>
                        {profile.display_name}
                      </option>
                    ))}
                  </select>
                  {selectedProfile ? (
                    <p className="helper-text">
                      {selectedProfile.profile_id === 'rafael_default'
                        ? 'Rafael Default is a demo/default profile, not global frontend logic.'
                        : selectedProfile.description}
                    </p>
                  ) : null}
                </section>

                <section className="control-section">
                  <div className="section-heading">
                    <h2>Capture health</h2>
                    <span>{captureHealth?.capture_mode ?? 'unknown'}</span>
                  </div>
                  <dl className="health-grid">
                    <div>
                      <dt>Mode</dt>
                      <dd>{captureHealth?.capture_mode ?? 'Unavailable'}</dd>
                    </div>
                    <div>
                      <dt>Browser automation</dt>
                      <dd>{captureHealth?.browser_automation_enabled ? 'Enabled' : 'Disabled'}</dd>
                    </div>
                    <div>
                      <dt>Last run</dt>
                      <dd>{captureHealth?.last_run_status ?? 'None'}</dd>
                    </div>
                  </dl>
                  {captureHealthError ? <p className="status-message">{captureHealthError}</p> : null}
                  {captureHealth?.warnings.map((warning) => (
                    <p className="inline-warning" key={warning}>
                      {warning}
                    </p>
                  ))}
                </section>

                <section className="control-section raw-input-section">
                  <div className="section-heading">
                    <h2>Staged raw jobs</h2>
                    <span>{stagedJobs.length} staged</span>
                  </div>
                  <label className="field-label" htmlFor="raw-job-text">
                    Raw job text
                  </label>
                  <textarea
                    id="raw-job-text"
                    value={rawJobText}
                    onChange={(event) => setRawJobText(event.target.value)}
                    rows={9}
                    placeholder="Paste one raw job listing here, then add it to the staged run."
                  />
                  <div className="button-row">
                    <button type="button" className="primary-button" onClick={addJob}>
                      Add job
                    </button>
                    <button type="button" className="secondary-button" onClick={loadDemoJobs}>
                      Load demo jobs
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        setStagedJobs([]);
                        setCaptureResult(null);
                        setExportResponses([]);
                        setExportError(null);
                      }}
                    >
                      Clear
                    </button>
                  </div>
                </section>

                {stagedJobs.length > 0 ? (
                  <section className="staged-list" aria-label="Staged raw jobs">
                    {stagedJobs.map((job, index) => (
                      <article key={`${index}-${job.slice(0, 20)}`}>
                        <div>
                          <strong>Job {index + 1}</strong>
                          <p>{job.slice(0, 180)}{job.length > 180 ? '...' : ''}</p>
                        </div>
                        <button type="button" onClick={() => removeStagedJob(index)}>
                          Remove
                        </button>
                      </article>
                    ))}
                  </section>
                ) : null}

                <button
                  type="button"
                  className="run-button"
                  disabled={captureLoading}
                  onClick={runReview}
                >
                  {captureLoading ? 'Running capture review...' : 'Run capture review'}
                </button>
                {captureError ? <p className="status-message">{captureError}</p> : null}
              </div>

              <div className="capture-results" aria-live="polite">
                {captureResult ? (
                  <>
                    <section className="review-overview">
                      <div className="section-heading">
                        <div>
                          <h2>Review dashboard</h2>
                          <p>{captureResult.run_id}</p>
                        </div>
                        <span>{captureResult.status}</span>
                      </div>
                      <div className="decision-overview-grid">
                        <SummaryMetric label="Apply" value={decisionCounts.Apply} />
                        <SummaryMetric label="Maybe" value={decisionCounts.Maybe} />
                        <SummaryMetric label="Discard" value={decisionCounts.Discard} />
                        <SummaryMetric label="Manual Review" value={decisionCounts['Manual Review']} />
                        <SummaryMetric label="Duplicate" value={decisionCounts.Duplicate} />
                        <SummaryMetric label="Errors" value={decisionCounts.Errors} />
                      </div>
                      <div className="run-compact-stats">
                        <span>Captured {captureResult.total_captured}</span>
                        <span>Parsed {captureResult.parsed_count}</span>
                        <span>Classified {captureResult.classified_count}</span>
                        <span>Failed {captureResult.failed_count}</span>
                      </div>
                      {captureResult.warnings.length > 0 ? (
                        <TextList title="Run warnings" items={captureResult.warnings} />
                      ) : null}
                    </section>

                    <section className="export-panel">
                      <div className="section-heading">
                        <div>
                          <h2>Export package</h2>
                          <p>Generate local files under backend/data/exports.</p>
                        </div>
                        <span>{exportResponses.length} generated</span>
                      </div>
                      <label className="checkbox-row">
                        <input
                          type="checkbox"
                          checked={includeRawTextInExport}
                          onChange={(event) => setIncludeRawTextInExport(event.target.checked)}
                        />
                        Include raw job text
                      </label>
                      <div className="button-row">
                        {(['json', 'csv', 'xlsx'] as ExportFormat[]).map((format) => (
                          <button
                            key={format}
                            type="button"
                            className="secondary-button"
                            disabled={exportLoading !== null}
                            onClick={() => runExport(format)}
                          >
                            {exportLoading === format ? `Exporting ${format.toUpperCase()}...` : `Export ${format.toUpperCase()}`}
                          </button>
                        ))}
                      </div>
                      {exportError ? <p className="status-message">{exportError}</p> : null}
                      {exportResponses.length > 0 ? (
                        <div className="export-results">
                          {exportResponses.map((response) => (
                            <article key={response.export_id}>
                              <strong>{response.export_id}</strong>
                              {response.files.map((file) => (
                                <code key={file}>{file}</code>
                              ))}
                              {response.warnings.map((warning) => (
                                <p key={warning}>{warning}</p>
                              ))}
                            </article>
                          ))}
                        </div>
                      ) : null}
                    </section>

                    <section className="filter-bar" aria-label="Decision filters">
                      {decisionFilters.map((filter) => (
                        <button
                          key={filter}
                          type="button"
                          className={filter === activeFilter ? 'filter-button active' : 'filter-button'}
                          onClick={() => setActiveFilter(filter)}
                        >
                          {filter} ({decisionCounts[filter]})
                        </button>
                      ))}
                    </section>

                    <section className="decision-list" aria-label="Capture review results">
                      {filteredResults.length > 0 ? (
                        filteredResults.map((result, index) => (
                          <DecisionCard key={`${result.raw_job.external_id ?? index}-${index}`} result={result} index={index} />
                        ))
                      ) : (
                        <p className="empty-state">No results match this filter.</p>
                      )}
                    </section>
                  </>
                ) : (
                  <section className="empty-state large">
                    <h2>Review results will appear here</h2>
                    <p>
                      Load demo jobs or paste raw job text, then run capture review to see parser +
                      decision engine results.
                    </p>
                  </section>
                )}
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
