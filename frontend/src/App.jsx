
import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const REFRESH_INTERVAL = 30000;

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [servers, setServers] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [incidentHistory, setIncidentHistory] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("all");

  const [awsData, setAwsData] = useState(null);
  const [cpuMetrics, setCpuMetrics] = useState({});
  const [investigations, setInvestigations] = useState({});
  const [investigating, setInvestigating] = useState({});
  const [investigationErrors, setInvestigationErrors] = useState({});
  const [selectedInvestigation, setSelectedInvestigation] = useState(null);

  const [error, setError] = useState("");
  const [awsError, setAwsError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshInProgress = useRef(false);

  const loadData = useCallback(async () => {
    if (refreshInProgress.current) return;

    refreshInProgress.current = true;
    setIsRefreshing(true);

    try {
      const [
        dashboardResponse,
        monitoringResponse,
        incidentsResponse,
        historyResponse,
      ] = await Promise.all([
        fetch(`${API_URL}/api/dashboard`),
        fetch(`${API_URL}/api/monitoring`),
        fetch(`${API_URL}/api/incidents`),
        fetch(`${API_URL}/api/incidents/history`),
      ]);

      if (
        !dashboardResponse.ok ||
        !monitoringResponse.ok ||
        !incidentsResponse.ok ||
        !historyResponse.ok
      ) {
        throw new Error("Failed to fetch monitoring data.");
      }

      const [
        dashboardData,
        monitoringData,
        incidentsData,
        historyData,
      ] = await Promise.all([
        dashboardResponse.json(),
        monitoringResponse.json(),
        incidentsResponse.json(),
        historyResponse.json(),
      ]);

      setDashboard(dashboardData);
      setServers(monitoringData.servers || []);
      setIncidents(incidentsData.incidents || []);

      setIncidentHistory(
        Array.isArray(historyData)
          ? historyData
          : historyData.incidents || []
      );

      setError("");
    } catch (err) {
      setError(
        err.message ||
          "Unable to load dashboard data. Check whether the backend is running."
      );
    }

    try {
      const response = await fetch(`${API_URL}/api/aws/instances`);

      if (!response.ok) {
        throw new Error(`AWS request failed (${response.status}).`);
      }

      const data = await response.json();

      setAwsData(data);
      setAwsError("");
      setLastUpdated(new Date());

      const runningInstances = (data.instances || []).filter(
        (instance) =>
          String(instance.status).toLowerCase() === "running"
      );

      const metricResults = await Promise.all(
        runningInstances.map(async (instance) => {
          try {
            const region = instance.region || data.region;

            const metricResponse = await fetch(
              `${API_URL}/api/aws/cpu/${encodeURIComponent(
                instance.id
              )}?region=${encodeURIComponent(region)}`
            );

            if (!metricResponse.ok) {
              throw new Error("Metric request failed.");
            }

            return [instance.id, await metricResponse.json()];
          } catch {
            return [
              instance.id,
              {
                success: false,
                message: "Unable to load CPU metrics.",
              },
            ];
          }
        })
      );

      setCpuMetrics(Object.fromEntries(metricResults));
    } catch (err) {
      setAwsError(
        err.message ||
          "Unable to load AWS instances. Check AWS credentials, permissions, and backend logs."
      );
    } finally {
      refreshInProgress.current = false;
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();

    const intervalId = setInterval(loadData, REFRESH_INTERVAL);

    return () => clearInterval(intervalId);
  }, [loadData]);

  async function investigateServer(server) {
    setInvestigating((previous) => ({
      ...previous,
      [server.id]: true,
    }));

    setInvestigationErrors((previous) => ({
      ...previous,
      [server.id]: "",
    }));

    try {
      const response = await fetch(
        `${API_URL}/api/ai/investigate/${encodeURIComponent(server.id)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to investigate this server."
        );
      }

      setInvestigations((previous) => ({
        ...previous,
        [server.id]: data.investigation,
      }));

      setSelectedInvestigation(server.id);

      // Reload history so saved investigation details appear immediately.
      await loadData();
    } catch (err) {
      setInvestigationErrors((previous) => ({
        ...previous,
        [server.id]: err.message || "Investigation failed.",
      }));
    } finally {
      setInvestigating((previous) => ({
        ...previous,
        [server.id]: false,
      }));
    }
  }

  if (!dashboard && error) {
    return (
      <main className="app">
        <h1>CloudOps AI</h1>
        <p className="error">{error}</p>
        <button type="button" onClick={loadData}>
          Retry connection
        </button>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className="app loading-screen">
        <div className="loading-spinner" />
        <h1>CloudOps AI</h1>
        <p>Loading your cloud operations dashboard...</p>
      </main>
    );
  }

  const selectedServer = servers.find(
    (server) => server.id === selectedInvestigation
  );

  const selectedResult = selectedInvestigation
    ? investigations[selectedInvestigation]
    : null;

  const filteredHistory = incidentHistory.filter((incident) => {
    if (historyFilter === "active") {
      return !incident.resolved_at;
    }

    if (historyFilter === "resolved") {
      return Boolean(incident.resolved_at);
    }

    if (historyFilter === "investigated") {
      return Boolean(incident.investigated_at);
    }

    if (historyFilter === "not-investigated") {
      return !incident.investigated_at;
    }

    return true;
  });

  return (
    <main className="app">
      {/* Dashboard header */}
      <header className="header">
        <div>
          <p className="eyebrow">CLOUD OPERATIONS PLATFORM</p>
          <h1>CloudOps AI</h1>
          <p className="subtitle">
            Monitor cloud resources, investigate incidents, and
            understand infrastructure health.
          </p>
        </div>

        <div
          className="header-actions"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            flexWrap: "wrap",
          }}
        >
          <StatusBadge
            status={
              awsError
                ? "error"
                : awsData
                  ? "connected"
                  : "loading"
            }
          />

          <span className="source-badge">AWS + SIMULATION</span>

          <button
            type="button"
            className="secondary-button refresh-button"
            onClick={loadData}
            disabled={isRefreshing}
            aria-label="Refresh dashboard data"
          >
            {isRefreshing ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      {/* Summary cards */}
      <section className="stats">
        <StatCard
          title="Simulated Servers"
          value={dashboard.total_servers}
          icon="◫"
        />

        <StatCard
          title="Running"
          value={dashboard.running_servers}
          icon="✓"
          accent="green"
        />

        <StatCard
          title="Stopped"
          value={dashboard.stopped_servers}
          icon="!"
          accent="red"
        />

        <StatCard
          title="Open Incidents"
          value={dashboard.active_incidents}
          icon="⚠"
          accent="orange"
        />
      </section>

      {/* Real AWS resources */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">LIVE INTEGRATION</p>
            <h2>Real AWS EC2 Instances</h2>
          </div>

          <StatusBadge
            status={
              awsError
                ? "error"
                : awsData
                  ? "connected"
                  : "loading"
            }
          />
        </div>

        {awsError ? (
          <p className="error">{awsError}</p>
        ) : !awsData ? (
          <p className="muted">Loading AWS resources...</p>
        ) : (
          <>
            <div className="aws-summary">
              <span>
                <strong>Region:</strong> {awsData.region}
              </span>

              <span>
                <strong>Total instances:</strong>{" "}
                {awsData.total_instances ??
                  (awsData.instances || []).length}
              </span>

              <span>
                <strong>Connection:</strong>{" "}
                {awsData.success ? "Connected" : "Check response"}
              </span>

              {lastUpdated && (
                <span>
                  <strong>Last refreshed:</strong>{" "}
                  {lastUpdated.toLocaleTimeString()}
                </span>
              )}
            </div>

            {!awsData.instances?.length ? (
              <div className="empty-state">
                <span className="empty-icon">☁</span>
                <h3>No EC2 instances found</h3>
                <p>
                  No EC2 instances were found in the configured AWS
                  region ({awsData.region}). This is a successful AWS
                  response, not a connection failure. Simulated
                  monitoring remains available below.
                </p>
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Instance Name</th>
                      <th>Instance ID</th>
                      <th>Type</th>
                      <th>Status</th>
                      <th>Average CPU</th>
                      <th>Maximum CPU</th>
                    </tr>
                  </thead>

                  <tbody>
                    {awsData.instances.map((instance) => {
                      const metrics = cpuMetrics[instance.id];

                      const getMetric = (metricName) => {
                        if (instance.status !== "running") {
                          return "Not running";
                        }

                        if (!metrics) return "Loading...";
                        if (!metrics.success) return "Unavailable";

                        const value = metrics[metricName];

                        return value == null
                          ? "No metrics"
                          : `${value}%`;
                      };

                      return (
                        <tr key={instance.id}>
                          <td>
                            <strong>{instance.name}</strong>
                          </td>
                          <td>
                            <code>{instance.id}</code>
                          </td>
                          <td>{instance.instance_type}</td>
                          <td>
                            <StatusBadge status={instance.status} />
                          </td>
                          <td>{getMetric("average_cpu")}</td>
                          <td>{getMetric("maximum_cpu")}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      {/* Simulated server monitoring */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">DEVELOPMENT ENVIRONMENT</p>
            <h2>Simulated Server Monitoring</h2>
          </div>

          <span className="source-badge simulation-badge">
            SIMULATED DATA
          </span>
        </div>

        <p className="section-description">
          Select Investigate to run the LangGraph workflow and view
          the diagnosis in a separate details panel.
        </p>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Server</th>
                <th>Region</th>
                <th>Status</th>
                <th>CPU Usage</th>
                <th>AI Investigation</th>
              </tr>
            </thead>

            <tbody>
              {servers.map((server) => (
                <tr key={server.id}>
                  <td>
                    <div className="server-name">
                      <strong>{server.name}</strong>
                      <small>{server.id}</small>
                    </div>
                  </td>

                  <td>{server.region}</td>

                  <td>
                    <StatusBadge status={server.status} />
                  </td>

                  <td>
                    <div className="cpu-cell">
                      <div
                        className="cpu-track"
                        role="progressbar"
                        aria-label={`${server.name} CPU usage`}
                        aria-valuenow={server.cpu_usage}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      >
                        <div
                          className={`cpu-fill ${
                            server.cpu_usage >= 80
                              ? "high"
                              : server.cpu_usage >= 60
                                ? "medium"
                                : ""
                          }`}
                          style={{
                            width: `${server.cpu_usage}%`,
                          }}
                        />
                      </div>

                      <span>{server.cpu_usage}%</span>
                    </div>
                  </td>

                  <td className="investigation-cell">
                    <button
                      type="button"
                      className="investigate-button"
                      onClick={() => investigateServer(server)}
                      disabled={investigating[server.id]}
                    >
                      {investigating[server.id]
                        ? "Investigating..."
                        : "✦ Investigate"}
                    </button>

                    {investigationErrors[server.id] && (
                      <p className="error investigation-error">
                        {investigationErrors[server.id]}
                      </p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* AI investigation details */}
      {selectedResult && (
        <section className="panel investigation-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">LANGGRAPH ANALYSIS</p>
              <h2>AI Investigation Details</h2>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={() => setSelectedInvestigation(null)}
            >
              Close ✕
            </button>
          </div>

          <div className="investigation-server">
            <span className="ai-icon">✦</span>

            <div>
              <h3>{selectedServer?.name || selectedInvestigation}</h3>
              <p>
                Server ID: {selectedInvestigation}
                {" · "}CPU: {selectedServer?.cpu_usage ?? "—"}%
                {" · "}Status: {selectedServer?.status ?? "Unknown"}
              </p>
            </div>

            <SeverityBadge severity={selectedResult.severity} />
          </div>

          <div className="investigation-details-grid">
            <article className="detail-card">
              <h3>Incident Type</h3>
              <p>{selectedResult.incident_type || "—"}</p>
            </article>

            <article className="detail-card">
              <h3>Diagnosis</h3>
              <p>{selectedResult.diagnosis || "No diagnosis available."}</p>
            </article>

            <article className="detail-card recommendation-card">
              <h3>Recommended Action</h3>
              <p>
                {selectedResult.recommendation ||
                  "No recommendation available."}
              </p>
            </article>
          </div>

          <p className="muted investigation-note">
            This investigation uses simulated server data and a
            rule-based LangGraph workflow. Recommendations are advisory;
            no AWS resources have been modified.
          </p>
        </section>
      )}

      {/* Active incidents */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">SYSTEM HEALTH</p>
            <h2>Detected Incidents</h2>
          </div>

          <span className="count-badge">
            {incidents.length} active
          </span>
        </div>

        {incidents.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">✓</span>
            <h3>No active incidents</h3>
            <p>
              All simulated servers are within the configured incident
              thresholds.
            </p>
          </div>
        ) : (
          <div className="incident-list">
            {incidents.map((incident, index) => {
              const matchingServer = servers.find(
                (server) => server.id === incident.server_id
              );

              return (
                <article
                  className="incident"
                  key={
                    incident.id ||
                    `${incident.server_id}-${incident.type}-${index}`
                  }
                >
                  <div className="incident-symbol">!</div>

                  <div className="incident-content">
                    <div className="incident-title">
                      <strong>{incident.server_name}</strong>
                      <SeverityBadge severity={incident.severity} />
                    </div>

                    <p>{incident.message}</p>
                    <small>{incident.type}</small>
                  </div>

                  {matchingServer && (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => investigateServer(matchingServer)}
                      disabled={investigating[matchingServer.id]}
                    >
                      {investigating[matchingServer.id]
                        ? "Investigating..."
                        : "Investigate"}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* Incident history */}
      <section className="panel incident-history-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AUDIT TRAIL</p>
            <h2>Incident History</h2>
            <p className="section-description">
              Review incident details, investigation results, and
              resolution timestamps.
            </p>
          </div>

          <span className="count-badge">
            {incidentHistory.length} records
          </span>
        </div>

        <div className="history-toolbar">
          <label htmlFor="history-filter">Filter incidents:</label>

          <select
            id="history-filter"
            value={historyFilter}
            onChange={(event) => setHistoryFilter(event.target.value)}
          >
            <option value="all">All incidents</option>
            <option value="active">Active</option>
            <option value="resolved">Resolved</option>
            <option value="investigated">Investigated</option>
            <option value="not-investigated">Not investigated</option>
          </select>

          <button
            type="button"
            className="secondary-button"
            onClick={loadData}
            disabled={isRefreshing}
          >
            Refresh history
          </button>
        </div>

        {filteredHistory.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">✓</span>
            <h3>No matching incidents</h3>
            <p>
              No incident records match your selected filter.
            </p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Incident Details</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Investigation</th>
                  <th>Recommended Action</th>
                  <th>Detected At</th>
                  <th>Investigated At</th>
                  <th>Resolved At</th>
                </tr>
              </thead>

              <tbody>
                {filteredHistory.map((incident) => (
                  <tr key={incident.id}>
                    <td>
                      <strong>
                        {incident.server_name || incident.server_id}
                      </strong>

                      <small className="history-subtext">
                        {incident.type}
                      </small>

                      <p className="history-message">
                        {incident.message}
                      </p>
                    </td>

                    <td>
                      <SeverityBadge severity={incident.severity} />
                    </td>

                    <td>
                      <span
                        className={`history-status ${
                          incident.resolved_at ? "resolved" : "active"
                        }`}
                      >
                        {incident.resolved_at ? "Resolved" : "Active"}
                      </span>
                    </td>

                    <td>
                      {incident.diagnosis ? (
                        <div>
                          <strong>Diagnosis</strong>
                          <p>{incident.diagnosis}</p>
                        </div>
                      ) : (
                        <span className="muted">
                          Not investigated
                        </span>
                      )}
                    </td>

                    <td>
                      {incident.recommendation || (
                        <span className="muted">
                          No recommendation yet
                        </span>
                      )}
                    </td>

                    <td>{formatTimestamp(incident.detected_at)}</td>

                    <td>
                      {incident.investigated_at ? (
                        <span className="history-investigated">
                          {formatTimestamp(incident.investigated_at)}
                        </span>
                      ) : (
                        <span className="muted">Not investigated</span>
                      )}
                    </td>

                    <td>{formatTimestamp(incident.resolved_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="footer">
        <span>CloudOps AI</span>
        <span>AWS read-only monitoring · CloudWatch · LangGraph</span>
      </footer>
    </main>
  );
}

function StatCard({ title, value, icon, accent = "" }) {
  return (
    <article className="stat-card">
      <div className="stat-card-top">
        <p>{title}</p>
        <span className={`stat-icon ${accent}`}>{icon}</span>
      </div>

      <strong className="stat-value">{value ?? "—"}</strong>
    </article>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || "unknown").toLowerCase();

  return (
    <span className={`status ${normalized}`}>
      <span className="status-dot" />
      {normalized}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const normalized = String(severity || "unknown").toLowerCase();

  return (
    <span className={`severity ${normalized}`}>
      {normalized}
    </span>
  );
}

export default App;
