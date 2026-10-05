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
  const [activeView, setActiveView] = useState("overview");

  const [dashboard, setDashboard] = useState(null);
  const [servers, setServers] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [incidentHistory, setIncidentHistory] = useState([]);

  const [historyFilter, setHistoryFilter] = useState("all");

  const [awsData, setAwsData] = useState(null);
  const [cpuMetrics, setCpuMetrics] = useState({});
  const [costData, setCostData] = useState(null);
  const [securityData, setSecurityData] = useState(null);

  const [investigations, setInvestigations] = useState({});
  const [investigating, setInvestigating] = useState({});
  const [selectedInvestigation, setSelectedInvestigation] = useState(null);

  const [remediationHistory, setRemediationHistory] = useState([]);
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [remediationMessage, setRemediationMessage] = useState("");

  // NEW: dashboard approval/rejection controls
  const [rejectModal, setRejectModal] = useState(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [remediationLoading, setRemediationLoading] = useState(false);

  const [error, setError] = useState("");
  const [awsError, setAwsError] = useState("");
  const [costError, setCostError] = useState("");
  const [securityError, setSecurityError] = useState("");

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const refreshInProgress = useRef(false);

  // ============================================================
  // LOAD DASHBOARD DATA
  // ============================================================

  const loadData = useCallback(async () => {
    if (refreshInProgress.current) return;

    refreshInProgress.current = true;
    setIsRefreshing(true);

    try {
      const responses = await Promise.all([
        fetch(`${API_URL}/api/dashboard`),
        fetch(`${API_URL}/api/monitoring`),
        fetch(`${API_URL}/api/incidents`),
        fetch(`${API_URL}/api/incidents/history`),
      ]);

      if (responses.some((response) => !response.ok)) {
        throw new Error("Failed to fetch dashboard data.");
      }

      const [dashboardData, monitoringData, incidentsData, historyData] =
        await Promise.all(responses.map((response) => response.json()));

      const normalizedIncidents = Array.isArray(incidentsData)
        ? incidentsData
        : incidentsData.incidents || [];

      setDashboard(dashboardData);

      setServers(monitoringData.servers || []);

      setIncidents(normalizedIncidents);

      setIncidentHistory(
        Array.isArray(historyData)
          ? historyData
          : historyData.history || historyData.incidents || [],
      );

      setError("");

      // ========================================================
      // AWS INSTANCES
      // ========================================================

      try {
        const response = await fetch(`${API_URL}/api/aws/instances`);

        if (!response.ok) {
          throw new Error(`AWS request failed (${response.status}).`);
        }

        const data = await response.json();

        setAwsData(data);
        setAwsError("");

        const runningInstances = (data.instances || []).filter(
          (instance) => String(instance.status).toLowerCase() === "running",
        );

        const metricResults = await Promise.all(
          runningInstances.map(async (instance) => {
            try {
              const region = instance.region || data.region;

              const metricResponse = await fetch(
                `${API_URL}/api/aws/cpu/${encodeURIComponent(
                  instance.id,
                )}?region=${encodeURIComponent(region)}`,
              );

              if (!metricResponse.ok) {
                throw new Error();
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
          }),
        );

        setCpuMetrics(Object.fromEntries(metricResults));
      } catch (err) {
        setAwsError(err.message || "Unable to load AWS instances.");
      }

      // ========================================================
      // AWS COST
      // ========================================================

      try {
        const response = await fetch(`${API_URL}/api/aws/cost`);

        if (!response.ok) {
          throw new Error(`Cost request failed (${response.status}).`);
        }

        const data = await response.json();

        setCostData(data);

        setCostError(
          data.success
            ? ""
            : data.errors?.[0] || "AWS cost data is unavailable.",
        );
      } catch (err) {
        setCostError(err.message || "Unable to load AWS cost information.");
      }

      // ========================================================
      // AWS SECURITY
      // ========================================================

      try {
        const response = await fetch(`${API_URL}/api/aws/security`);

        if (!response.ok) {
          throw new Error(`Security request failed (${response.status}).`);
        }

        setSecurityData(await response.json());

        setSecurityError("");
      } catch (err) {
        setSecurityError(
          err.message || "Unable to load AWS security analysis.",
        );
      }

      // ========================================================
      // REMEDIATION HISTORY
      // ========================================================

      try {
        const response = await fetch(`${API_URL}/api/remediation/history`);

        if (response.ok) {
          const data = await response.json();

          setRemediationHistory(
            Array.isArray(data) ? data : data.history || data.approvals || [],
          );
        }
      } catch {
        // Optional feature.
      }

      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "Unable to load dashboard data.");
    } finally {
      refreshInProgress.current = false;
      setIsRefreshing(false);
    }
  }, []);

  // ============================================================
  // AUTO REFRESH
  // ============================================================

  useEffect(() => {
    loadData();

    const interval = setInterval(loadData, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [loadData]);

  // ============================================================
  // AI INVESTIGATION
  // ============================================================

  async function investigateServer(server) {
    setInvestigating((previous) => ({
      ...previous,
      [server.id]: true,
    }));

    try {
      const response = await fetch(
        `${API_URL}/api/ai/investigate/${encodeURIComponent(server.id)}`,
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to investigate server.");
      }

      setInvestigations((previous) => ({
        ...previous,
        [server.id]: data.investigation,
      }));

      setSelectedInvestigation(server.id);
      setActiveView("ai");

      await loadData();
    } catch (err) {
      setError(err.message || "Investigation failed.");
    } finally {
      setInvestigating((previous) => ({
        ...previous,
        [server.id]: false,
      }));
    }
  }

  // ============================================================
  // REMEDIATION
  // ============================================================

  async function createProposal(incident) {
    setRemediationMessage("");

    try {
      const response = await fetch(`${API_URL}/api/remediation/propose`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          server_id: incident.server_id,
          server_name: incident.server_name || incident.server_id,
          incident_type: incident.type || "incident",
          severity: incident.severity || "medium",
          message: incident.message || "",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to create remediation proposal.",
        );
      }

      if (!data.proposal) {
        throw new Error("The backend did not return a remediation proposal.");
      }

      setSelectedProposal(data.proposal);

      setRemediationMessage(
        "Remediation proposal created. Human approval is required.",
      );

      setActiveView("remediation");

      await loadData();
    } catch (err) {
      console.error("Create remediation proposal error:", err);

      setRemediationMessage(
        err.message || "Unable to create remediation proposal.",
      );
    }
  }

  // ============================================================
  // APPROVE PROPOSAL
  // ============================================================

  async function approveProposal(proposal = selectedProposal) {
    if (!proposal?.proposal_id) {
      setRemediationMessage("No remediation proposal is selected.");
      return;
    }

    setRemediationLoading(true);
    setRemediationMessage("");

    try {
      const response = await fetch(
        `${API_URL}/api/remediation/${encodeURIComponent(
          proposal.proposal_id,
        )}/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            approver: "admin",
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Approval failed.");
      }

      const updatedProposal = data.proposal || data;

      setSelectedProposal(updatedProposal);

      setRemediationMessage("✓ Proposal approved successfully.");

      await loadData();
    } catch (err) {
      console.error("Approval error:", err);

      setRemediationMessage(err.message || "Approval failed.");
    } finally {
      setRemediationLoading(false);
    }
  }

  // ============================================================
  // OPEN REJECT MODAL
  // ============================================================

  function openRejectModal(proposal = selectedProposal) {
    if (!proposal?.proposal_id) {
      setRemediationMessage("No remediation proposal is selected.");
      return;
    }

    setRejectModal(proposal);
    setRejectionReason("");
  }

  // ============================================================
  // REJECT PROPOSAL
  // ============================================================

  async function rejectProposal() {
    if (!rejectModal?.proposal_id) {
      return;
    }

    setRemediationLoading(true);
    setRemediationMessage("");

    const reason =
      rejectionReason.trim() || "Rejected from CloudOps AI dashboard.";

    try {
      const response = await fetch(
        `${API_URL}/api/remediation/${encodeURIComponent(
          rejectModal.proposal_id,
        )}/reject`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            approver: "admin",

            // IMPORTANT:
            // The backend audit workflow expects
            // rejection_reason.
            rejection_reason: reason,
          }),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Rejection failed.");
      }

      const updatedProposal = data.proposal || data;

      setSelectedProposal(updatedProposal);

      setRejectModal(null);
      setRejectionReason("");

      setRemediationMessage(
        "✓ Proposal rejected and recorded in the audit trail.",
      );

      await loadData();
    } catch (err) {
      console.error("Rejection error:", err);

      setRemediationMessage(err.message || "Rejection failed.");
    } finally {
      setRemediationLoading(false);
    }
  }

  // ============================================================
  // EXECUTE PROPOSAL
  // ============================================================

  async function executeProposal() {
    if (!selectedProposal?.proposal_id) {
      setRemediationMessage("No remediation proposal is selected.");
      return;
    }

    setRemediationLoading(true);
    setRemediationMessage("");

    try {
      const response = await fetch(
        `${API_URL}/api/remediation/${encodeURIComponent(
          selectedProposal.proposal_id,
        )}/execute`,
        {
          method: "POST",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Execution failed.");
      }

      const updatedProposal = data.proposal || data;

      setSelectedProposal(updatedProposal);

      setRemediationMessage(
        data.aws_modified === false
          ? "✓ Simulation completed. No AWS resources were modified."
          : "Execution completed.",
      );

      await loadData();
    } catch (err) {
      console.error("Execution error:", err);

      setRemediationMessage(err.message || "Execution failed.");
    } finally {
      setRemediationLoading(false);
    }
  }

  // ============================================================
  // FILTER HISTORY
  // ============================================================

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

  const selectedServer = servers.find(
    (server) => server.id === selectedInvestigation,
  );

  const selectedResult = selectedInvestigation
    ? investigations[selectedInvestigation]
    : null;

  // ============================================================
  // LOADING
  // ============================================================

  if (!dashboard && !error) {
    return (
      <div className="startup-screen">
        <div className="startup-card">
          <div className="brand-mark large">C</div>

          <div className="loading-spinner" />

          <h1>CloudOps AI</h1>

          <p>Loading cloud operations data...</p>
        </div>
      </div>
    );
  }

  if (!dashboard && error) {
    return (
      <div className="startup-screen">
        <div className="startup-card">
          <div className="brand-mark large">C</div>

          <h1>CloudOps AI</h1>

          <p>{error}</p>

          <button className="primary-button" onClick={loadData}>
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* =====================================================
          SIDEBAR
      ===================================================== */}

      <Sidebar activeView={activeView} setActiveView={setActiveView} />

      {/* =====================================================
          MAIN
      ===================================================== */}

      <div className="main-shell">
        <Topbar
          activeView={activeView}
          lastUpdated={lastUpdated}
          isRefreshing={isRefreshing}
          awsConnected={Boolean(awsData) && !awsError}
          onRefresh={loadData}
        />

        <main className="main-content">
          {error && <div className="global-error">{error}</div>}

          {/* OVERVIEW */}

          {activeView === "overview" && (
            <Overview
              dashboard={dashboard}
              servers={servers}
              incidents={incidents}
              awsData={awsData}
              securityData={securityData}
              costData={costData}
              onNavigate={setActiveView}
            />
          )}

          {/* MONITORING */}

          {activeView === "monitoring" && (
            <MonitoringView
              servers={servers}
              awsData={awsData}
              cpuMetrics={cpuMetrics}
              awsError={awsError}
              investigating={investigating}
              investigateServer={investigateServer}
            />
          )}

          {/* INCIDENTS */}

          {activeView === "incidents" && (
            <IncidentsView
              incidents={incidents}
              servers={servers}
              investigating={investigating}
              investigateServer={investigateServer}
              createProposal={createProposal}
            />
          )}

          {/* AI */}

          {activeView === "ai" && (
            <AIView
              servers={servers}
              investigations={investigations}
              selectedServer={selectedServer}
              selectedResult={selectedResult}
              selectedInvestigation={selectedInvestigation}
              setSelectedInvestigation={setSelectedInvestigation}
              investigating={investigating}
              investigateServer={investigateServer}
            />
          )}

          {/* SECURITY */}

          {activeView === "security" && (
            <SecurityView
              securityData={securityData}
              securityError={securityError}
              onRefresh={loadData}
            />
          )}

          {/* COST */}

          {activeView === "cost" && (
            <CostView costData={costData} costError={costError} />
          )}

          {/* REMEDIATION */}

          {activeView === "remediation" && (
            <RemediationView
              incidents={incidents}
              selectedProposal={selectedProposal}
              setSelectedProposal={setSelectedProposal}
              remediationHistory={remediationHistory}
              remediationMessage={remediationMessage}
              createProposal={createProposal}
              approveProposal={approveProposal}
              openRejectModal={openRejectModal}
              executeProposal={executeProposal}
              remediationLoading={remediationLoading}
              rejectModal={rejectModal}
              rejectionReason={rejectionReason}
              setRejectionReason={setRejectionReason}
              setRejectModal={setRejectModal}
              rejectProposal={rejectProposal}
            />
          )}

          {/* HISTORY */}

          {activeView === "history" && (
            <HistoryView
              filteredHistory={filteredHistory}
              historyFilter={historyFilter}
              setHistoryFilter={setHistoryFilter}
              incidentHistory={incidentHistory}
            />
          )}

          {/* SETTINGS */}

          {activeView === "settings" && <SettingsView />}
        </main>
      </div>
    </div>
  );
}

/* ============================================================
   SIDEBAR
============================================================ */

function Sidebar({ activeView, setActiveView }) {
  const items = [
    ["overview", "⌂", "Overview"],
    ["monitoring", "◉", "Monitoring"],
    ["incidents", "!", "Incidents"],
    ["ai", "✦", "AI Investigation"],
    ["security", "◇", "Security"],
    ["cost", "$", "Cost Analysis"],
    ["remediation", "⚡", "Remediation"],
    ["history", "◷", "History"],
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">C</div>

        <div>
          <h1>CloudOps AI</h1>
          <span>AI OPERATIONS</span>
        </div>
      </div>

      <div className="sidebar-section">
        <span className="sidebar-label">WORKSPACE</span>

        <nav className="sidebar-nav">
          {items.map(([id, icon, label]) => (
            <button
              key={id}
              className={`nav-item ${activeView === id ? "active" : ""}`}
              onClick={() => setActiveView(id)}
            >
              <span className="nav-icon">{icon}</span>

              <span>{label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <button
          className={`nav-item ${activeView === "settings" ? "active" : ""}`}
          onClick={() => setActiveView("settings")}
        >
          <span className="nav-icon">⚙</span>

          <span>Settings</span>
        </button>

        <div className="sidebar-status">
          <span className="status-dot" />

          <div>
            <strong>System Online</strong>

            <small>Read-only AWS monitoring</small>
          </div>
        </div>
      </div>
    </aside>
  );
}

/* ============================================================
   TOPBAR
============================================================ */

function Topbar({
  activeView,
  lastUpdated,
  isRefreshing,
  awsConnected,
  onRefresh,
}) {
  const titles = {
    overview: ["Overview", "Cloud infrastructure at a glance"],

    monitoring: ["Monitoring", "Infrastructure health and resource metrics"],

    incidents: ["Incidents", "Active infrastructure incidents"],

    ai: ["AI Investigation", "Multi-agent incident analysis"],

    security: ["Security", "AWS security findings and exposure analysis"],

    cost: ["Cost Analysis", "AWS usage and cost insights"],

    remediation: ["Remediation", "Approval-gated infrastructure actions"],

    history: ["History", "Incident and remediation audit trail"],

    settings: ["Settings", "CloudOps AI configuration"],
  };

  const [title, description] = titles[activeView];

  return (
    <header className="topbar">
      <div className="topbar-title">
        <h2>{title}</h2>

        <p>{description}</p>
      </div>

      <div className="topbar-actions">
        <div className="connection-status">
          <span className={`status-dot ${awsConnected ? "" : "offline"}`} />

          {awsConnected ? "AWS Connected" : "AWS Unavailable"}
        </div>

        {lastUpdated && (
          <span className="last-updated">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}

        <button
          className="refresh-button"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <span className={isRefreshing ? "spinning" : ""}>↻</span>

          {isRefreshing ? "Refreshing" : "Refresh"}
        </button>
      </div>
    </header>
  );
}

/* ============================================================
   OVERVIEW
============================================================ */

function Overview({
  dashboard,
  servers,
  incidents,
  awsData,
  securityData,
  costData,
  onNavigate,
}) {
  return (
    <div className="view">
      <div className="page-intro">
        <div>
          <span className="eyebrow">CLOUD OPERATIONS PLATFORM</span>

          <h3>Infrastructure Overview</h3>

          <p>
            Monitor resources, investigate incidents, review security and
            control remediation from one workspace.
          </p>
        </div>

        <span className="environment-badge">
          <span className="status-dot" />
          AWS + Simulation
        </span>
      </div>

      <section className="stats-grid">
        <MetricCard
          label="TOTAL SERVERS"
          value={dashboard.total_servers ?? servers.length}
          note="Tracked resources"
        />

        <MetricCard
          label="RUNNING"
          value={dashboard.running_servers ?? 0}
          note="Operational"
          tone="green"
        />

        <MetricCard
          label="OPEN INCIDENTS"
          value={dashboard.active_incidents ?? incidents.length}
          note={incidents.length ? "Requires attention" : "No active incidents"}
          tone={incidents.length ? "orange" : "green"}
        />

        <MetricCard
          label="AVERAGE CPU"
          value={`${dashboard.average_cpu ?? "—"}%`}
          note="Current workload"
        />
      </section>

      <div className="overview-grid">
        <Panel title="System Health" eyebrow="INFRASTRUCTURE">
          <HealthRow
            icon="✓"
            tone="green"
            label="Running servers"
            value={dashboard.running_servers ?? 0}
          />

          <HealthRow
            icon="!"
            tone="gray"
            label="Stopped servers"
            value={dashboard.stopped_servers ?? 0}
          />

          <HealthRow
            icon="!"
            tone="orange"
            label="High severity incidents"
            value={dashboard.high_severity_incidents ?? 0}
          />

          <HealthRow
            icon="!"
            tone="red"
            label="Critical incidents"
            value={
              dashboard.critical_incidents ??
              dashboard.critical_severity_incidents ??
              0
            }
          />
        </Panel>

        <Panel
          title="Active Incidents"
          eyebrow="INCIDENT CENTER"
          badge={`${incidents.length} active`}
        >
          {incidents.length === 0 ? (
            <EmptyState
              icon="✓"
              title="No active incidents"
              text="Your monitored environment is currently healthy."
            />
          ) : (
            <div className="incident-preview">
              {incidents.slice(0, 5).map((incident, index) => (
                <div
                  className="incident-row"
                  key={incident.id || `${incident.server_id}-${index}`}
                >
                  <div>
                    <strong>
                      {incident.server_name || incident.server_id}
                    </strong>

                    <span>{incident.type}</span>
                  </div>

                  <SeverityBadge severity={incident.severity} />
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="Cloud Snapshot" eyebrow="AWS READ-ONLY">
        <div className="snapshot-grid">
          <SnapshotItem label="Region" value={awsData?.region || "—"} />

          <SnapshotItem
            label="EC2 Instances"
            value={awsData?.total_instances ?? 0}
          />

          <SnapshotItem
            label="Security Findings"
            value={securityData?.total_findings ?? 0}
          />

          <SnapshotItem
            label="Current Cost"
            value={
              costData?.success
                ? `${costData.currency || "USD"} ${Number(
                    costData.total_cost || 0,
                  ).toFixed(2)}`
                : "Unavailable"
            }
          />
        </div>
      </Panel>

      <div className="quick-actions">
        <button onClick={() => onNavigate("monitoring")}>
          Open Monitoring
        </button>

        <button onClick={() => onNavigate("incidents")}>
          Review Incidents
        </button>

        <button onClick={() => onNavigate("security")}>Security Scan</button>

        <button onClick={() => onNavigate("remediation")}>
          Remediation Center
        </button>
      </div>
    </div>
  );
}

/* ============================================================
   MONITORING
============================================================ */

function MonitoringView({
  servers,
  awsData,
  cpuMetrics,
  awsError,
  investigating,
  investigateServer,
}) {
  return (
    <div className="view">
      <PageHeading
        eyebrow="RESOURCE MONITORING"
        title="Infrastructure Monitoring"
        text="Monitor simulated development servers and real AWS EC2 resources."
      />

      <Panel
        title="Simulated Servers"
        eyebrow="DEVELOPMENT ENVIRONMENT"
        badge={`${servers.length} servers`}
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Server</th>
                <th>Region</th>
                <th>Status</th>
                <th>CPU</th>
                <th>AI</th>
              </tr>
            </thead>

            <tbody>
              {servers.map((server) => (
                <tr key={server.id}>
                  <td>
                    <strong>{server.name}</strong>

                    <small>{server.id}</small>
                  </td>

                  <td>{server.region || "—"}</td>

                  <td>
                    <StatusBadge status={server.status} />
                  </td>

                  <td>
                    <div className="cpu-cell">
                      <div className="cpu-track">
                        <div
                          className={`cpu-fill ${
                            server.cpu_usage >= 80
                              ? "high"
                              : server.cpu_usage >= 60
                                ? "medium"
                                : ""
                          }`}
                          style={{
                            width: `${Math.min(server.cpu_usage || 0, 100)}%`,
                          }}
                        />
                      </div>

                      <span>{server.cpu_usage ?? 0}%</span>
                    </div>
                  </td>

                  <td>
                    <button
                      className="small-button"
                      onClick={() => investigateServer(server)}
                      disabled={investigating[server.id]}
                    >
                      {investigating[server.id]
                        ? "Working..."
                        : "✦ Investigate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title="Real AWS EC2"
        eyebrow="LIVE AWS INTEGRATION"
        badge={
          awsData ? `${awsData.total_instances ?? 0} instances` : "Loading"
        }
      >
        {awsError ? (
          <div className="inline-error">{awsError}</div>
        ) : !awsData?.instances?.length ? (
          <EmptyState
            icon="☁"
            title="No EC2 instances found"
            text={
              awsData
                ? `No EC2 instances were found in ${awsData.region}.`
                : "Loading AWS resources..."
            }
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
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

                  const metric = (name) => {
                    if (instance.status !== "running") {
                      return "Not running";
                    }

                    if (!metrics) {
                      return "Loading...";
                    }

                    if (!metrics.success) {
                      return "Unavailable";
                    }

                    return metrics[name] == null
                      ? "No metrics"
                      : `${metrics[name]}%`;
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

                      <td>{metric("average_cpu")}</td>

                      <td>{metric("maximum_cpu")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

/* ============================================================
   INCIDENTS
============================================================ */

function IncidentsView({
  incidents,
  servers,
  investigating,
  investigateServer,
  createProposal,
}) {
  return (
    <div className="view">
      <PageHeading
        eyebrow="INCIDENT CENTER"
        title="Detected Incidents"
        text="Review active incidents and send them to AI investigation or remediation."
      />

      {incidents.length === 0 ? (
        <Panel>
          <EmptyState
            icon="✓"
            title="No active incidents"
            text="All monitored servers are currently within configured thresholds."
          />
        </Panel>
      ) : (
        <div className="incident-stack">
          {incidents.map((incident, index) => {
            const server = servers.find(
              (item) => item.id === incident.server_id,
            );

            return (
              <article
                className="incident-card"
                key={incident.id || `${incident.server_id}-${index}`}
              >
                <div className="incident-symbol">!</div>

                <div className="incident-content">
                  <div className="incident-title">
                    <strong>
                      {incident.server_name || incident.server_id}
                    </strong>

                    <SeverityBadge severity={incident.severity} />
                  </div>

                  <p>{incident.message}</p>

                  <small>{incident.type}</small>
                </div>

                <div className="incident-actions">
                  {server && (
                    <button
                      className="secondary-button"
                      onClick={() => investigateServer(server)}
                      disabled={investigating[server.id]}
                    >
                      {investigating[server.id]
                        ? "Investigating..."
                        : "✦ Investigate"}
                    </button>
                  )}

                  <button
                    className="primary-button"
                    onClick={() => createProposal(incident)}
                  >
                    ⚡ Remediate
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ============================================================
   AI INVESTIGATION
============================================================ */

function AIView({
  servers,
  investigations,
  selectedServer,
  selectedResult,
  selectedInvestigation,
  setSelectedInvestigation,
  investigating,
  investigateServer,
}) {
  return (
    <div className="view">
      <PageHeading
        eyebrow="LANGGRAPH ANALYSIS"
        title="AI Investigation"
        text="Run the investigation workflow against a monitored server."
      />

      <Panel title="Investigation Targets" eyebrow="SIMULATED INFRASTRUCTURE">
        <div className="ai-server-grid">
          {servers.map((server) => (
            <div
              className={`ai-server-card ${
                selectedInvestigation === server.id ? "selected" : ""
              }`}
              key={server.id}
              onClick={() => setSelectedInvestigation(server.id)}
            >
              <div>
                <strong>{server.name}</strong>

                <span>{server.id}</span>
              </div>

              <StatusBadge status={server.status} />

              <small>CPU {server.cpu_usage ?? 0}%</small>

              <button
                className="small-button"
                onClick={(event) => {
                  event.stopPropagation();

                  investigateServer(server);
                }}
                disabled={investigating[server.id]}
              >
                {investigating[server.id] ? "Investigating..." : "Investigate"}
              </button>
            </div>
          ))}
        </div>
      </Panel>

      {selectedResult ? (
        <Panel title="Investigation Details" eyebrow="AI DIAGNOSIS">
          <div className="investigation-header">
            <div className="ai-icon">✦</div>

            <div>
              <strong>{selectedServer?.name || selectedInvestigation}</strong>

              <span>
                {selectedInvestigation} · CPU {selectedServer?.cpu_usage ?? "—"}
                %
              </span>
            </div>
          </div>

          <div className="detail-grid">
            <DetailCard
              title="Incident Type"
              value={selectedResult.incident_type || "—"}
            />

            <DetailCard
              title="Diagnosis"
              value={selectedResult.diagnosis || "No diagnosis available."}
            />

            <DetailCard
              title="Recommended Action"
              value={
                selectedResult.recommendation || "No recommendation available."
              }
              emphasis
            />
          </div>

          <p className="safety-note">
            AI investigation is advisory and does not modify AWS resources.
          </p>
        </Panel>
      ) : (
        <Panel>
          <EmptyState
            icon="✦"
            title="Select a server to investigate"
            text="The investigation result will appear here."
          />
        </Panel>
      )}
    </div>
  );
}

/* ============================================================
   SECURITY
============================================================ */

function SecurityView({ securityData, securityError, onRefresh }) {
  if (securityError) {
    return (
      <div className="view">
        <PageHeading
          eyebrow="SECURITY MONITORING"
          title="AWS Security"
          text="Read-only EC2 security analysis."
        />

        <Panel>
          <div className="inline-error">{securityError}</div>

          <button className="secondary-button" onClick={onRefresh}>
            Retry Security Scan
          </button>
        </Panel>
      </div>
    );
  }

  if (!securityData) {
    return (
      <LoadingView title="AWS Security" text="Running security analysis..." />
    );
  }

  const counts = securityData.severity_counts || {};

  return (
    <div className="view">
      <PageHeading
        eyebrow="SECURITY MONITORING"
        title="AWS Security"
        text="Read-only analysis of available EC2 infrastructure."
      />

      <section className="stats-grid">
        <MetricCard
          label="STATUS"
          value={String(securityData.overall_status || "unknown").toUpperCase()}
          tone={securityData.overall_status === "critical" ? "red" : "green"}
        />

        <MetricCard
          label="TOTAL FINDINGS"
          value={securityData.total_findings ?? 0}
          tone={securityData.total_findings ? "orange" : "green"}
        />

        <MetricCard label="CRITICAL" value={counts.critical ?? 0} tone="red" />

        <MetricCard label="HIGH" value={counts.high ?? 0} tone="orange" />
      </section>

      <Panel title="Scan Coverage" eyebrow="AWS">
        <div className="snapshot-grid">
          <SnapshotItem
            label="Scan Status"
            value={securityData.scan_status || "unknown"}
          />

          <SnapshotItem
            label="Regions"
            value={`${securityData.successful_regions ?? 0}/${securityData.total_regions ?? 0}`}
          />

          <SnapshotItem
            label="Failed Regions"
            value={securityData.failed_regions ?? 0}
          />

          <SnapshotItem
            label="EC2 Instances"
            value={securityData.total_instances ?? 0}
          />
        </div>
      </Panel>

      <Panel title="Security Findings" eyebrow="ANALYSIS">
        {(securityData.findings || []).length === 0 ? (
          <EmptyState
            icon="✓"
            title="No security findings"
            text="No security findings were returned."
          />
        ) : (
          <div className="finding-list">
            {securityData.findings.map((finding, index) => (
              <article
                className="finding-card"
                key={finding.id || `${finding.type}-${index}`}
              >
                <div className="incident-symbol">!</div>

                <div>
                  <div className="incident-title">
                    <strong>
                      {finding.title || finding.type || "Security Finding"}
                    </strong>

                    <SeverityBadge severity={finding.severity || "medium"} />
                  </div>

                  <p>
                    {finding.message ||
                      finding.description ||
                      "No description available."}
                  </p>

                  {finding.recommendation && (
                    <small>
                      <strong>Recommendation:</strong> {finding.recommendation}
                    </small>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

/* ============================================================
   COST
============================================================ */

function CostView({ costData, costError }) {
  if (!costData) {
    return (
      <LoadingView
        title="Cost Analysis"
        text="Loading AWS cost information..."
      />
    );
  }

  if (!costData.success) {
    return (
      <div className="view">
        <PageHeading
          eyebrow="COST MANAGEMENT"
          title="AWS Cost Analysis"
          text="AWS Cost Explorer information."
        />

        <Panel>
          <EmptyState
            icon="$"
            title="Cost data is not available yet"
            text={
              costError ||
              costData.errors?.[0] ||
              "AWS has not returned cost data yet."
            }
          />
        </Panel>
      </div>
    );
  }

  return (
    <div className="view">
      <PageHeading
        eyebrow="COST MANAGEMENT"
        title="AWS Cost Analysis"
        text="Review cost by AWS service and region."
      />

      <section className="stats-grid">
        <MetricCard
          label="TOTAL COST"
          value={`$${Number(costData.total_cost || 0).toFixed(2)}`}
          tone="green"
        />

        <MetricCard label="SERVICES" value={costData.services?.length || 0} />

        <MetricCard label="REGIONS" value={costData.regions?.length || 0} />

        <MetricCard label="CURRENCY" value={costData.currency || "USD"} />
      </section>

      <Panel title="Service Costs" eyebrow="AWS COST EXPLORER">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>AWS Service</th>
                <th>Cost</th>
              </tr>
            </thead>

            <tbody>
              {(costData.services || []).map((service) => (
                <tr key={service.service}>
                  <td>
                    <strong>{service.service}</strong>
                  </td>

                  <td>${Number(service.cost || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Regional Costs" eyebrow="AWS REGIONS">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Region</th>
                <th>Cost</th>
              </tr>
            </thead>

            <tbody>
              {(costData.regions || []).map((region) => (
                <tr key={region.region}>
                  <td>
                    <strong>{region.region}</strong>
                  </td>

                  <td>${Number(region.cost || 0).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

/* ============================================================
   REMEDIATION
============================================================ */

function RemediationView({
  incidents,
  selectedProposal,
  setSelectedProposal,
  remediationHistory,
  remediationMessage,
  createProposal,
  approveProposal,
  openRejectModal,
  executeProposal,
  remediationLoading,

  // Rejection modal props
  rejectModal,
  rejectionReason,
  setRejectionReason,
  setRejectModal,
  rejectProposal,
}) {
  return (
    <div className="view">
      <PageHeading
        eyebrow="POLICY GATE"
        title="Remediation Center"
        text="Create proposals, review risk, require human approval, and execute only safe approved simulations."
      />

      {remediationMessage && (
        <div className="info-banner">
          <span className="info-banner-icon">●</span>

          <span>{remediationMessage}</span>
        </div>
      )}

      {/* ======================================================
          INCIDENT PROPOSALS
      ====================================================== */}

      <Panel
        title="Open Incident Proposals"
        eyebrow="PROPOSALS"
        badge={`${incidents.length} incidents`}
      >
        {incidents.length === 0 ? (
          <EmptyState
            icon="✓"
            title="No incidents available"
            text="There are no active incidents requiring remediation."
          />
        ) : (
          <div className="proposal-list">
            {incidents.map((incident, index) => (
              <article
                className="proposal-row"
                key={incident.id || `${incident.server_id}-${index}`}
              >
                <div className="proposal-row-info">
                  <div className="proposal-server-icon">⚡</div>

                  <div>
                    <strong>
                      {incident.server_name || incident.server_id}
                    </strong>

                    <span>
                      {incident.type || "Infrastructure incident"}

                      {" · "}

                      <SeverityBadge severity={incident.severity || "medium"} />
                    </span>
                  </div>
                </div>

                <button
                  className="primary-button"
                  onClick={() => createProposal(incident)}
                  disabled={remediationLoading}
                >
                  {remediationLoading ? "Working..." : "Create Proposal"}
                </button>
              </article>
            ))}
          </div>
        )}
      </Panel>

      {/* ======================================================
          SELECTED PROPOSAL
      ====================================================== */}

      {selectedProposal && (
        <Panel
          title="Selected Proposal"
          eyebrow="HUMAN APPROVAL"
          badge={selectedProposal.approval_status || "pending_approval"}
        >
          <div className="proposal-header">
            <div>
              <span className="eyebrow">PROPOSAL ID</span>

              <strong>{selectedProposal.proposal_id}</strong>

              <span>
                {selectedProposal.server_name}
                {" · "}
                {selectedProposal.action}
              </span>
            </div>

            <StatusBadge
              status={selectedProposal.approval_status || "pending_approval"}
            />
          </div>

          <div className="detail-grid">
            <DetailCard
              title="Action"
              value={
                selectedProposal.action_description ||
                selectedProposal.action ||
                "—"
              }
            />

            <DetailCard title="Reason" value={selectedProposal.reason || "—"} />

            <DetailCard
              title="Impact"
              value={selectedProposal.impact || "—"}
              emphasis
            />

            <DetailCard
              title="Rollback"
              value={selectedProposal.rollback || "Not specified."}
            />
          </div>

          {selectedProposal.preconditions?.length > 0 && (
            <div className="proposal-section">
              <span className="eyebrow">PRECONDITIONS</span>

              <ul className="proposal-list-details">
                {selectedProposal.preconditions.map((item, index) => (
                  <li key={index}>
                    <span>✓</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {selectedProposal.verification_plan?.length > 0 && (
            <div className="proposal-section">
              <span className="eyebrow">VERIFICATION PLAN</span>

              <ul className="proposal-list-details">
                {selectedProposal.verification_plan.map((item, index) => (
                  <li key={index}>
                    <span>→</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="proposal-actions">
            {selectedProposal.approval_status === "pending_approval" && (
              <>
                <button
                  className="approve-button large"
                  onClick={() => approveProposal(selectedProposal)}
                  disabled={remediationLoading}
                >
                  {remediationLoading ? "Processing..." : "✓ Approve Proposal"}
                </button>

                <button
                  className="reject-button large"
                  onClick={() => openRejectModal(selectedProposal)}
                  disabled={remediationLoading}
                >
                  ✕ Reject Proposal
                </button>
              </>
            )}

            {selectedProposal.approval_status === "approved" &&
              selectedProposal.execution_status !== "simulated" && (
                <button
                  className="execute-button"
                  onClick={executeProposal}
                  disabled={remediationLoading}
                >
                  {remediationLoading
                    ? "Executing..."
                    : "⚡ Execute Safe Simulation"}
                </button>
              )}

            {selectedProposal.execution_status === "simulated" && (
              <div className="simulation-complete">
                <span>✓</span>

                <div>
                  <strong>Simulation completed</strong>

                  <small>No AWS resources were modified.</small>
                </div>
              </div>
            )}

            <button
              className="secondary-button"
              onClick={() => setSelectedProposal(null)}
              disabled={remediationLoading}
            >
              Close
            </button>
          </div>
        </Panel>
      )}

      {/* ======================================================
          AUDIT HISTORY
      ====================================================== */}

      <Panel
        title="Remediation Audit"
        eyebrow="POSTGRESQL"
        badge={`${remediationHistory.length} records`}
      >
        {remediationHistory.length === 0 ? (
          <EmptyState
            icon="◷"
            title="No remediation records"
            text="Approval, rejection and execution records will appear here."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Server</th>
                  <th>Action</th>
                  <th>Approval</th>
                  <th>Execution</th>
                  <th>Approver</th>
                  <th>Created</th>
                  <th>Control</th>
                </tr>
              </thead>

              <tbody>
                {remediationHistory.map((row) => (
                  <tr key={row.id || row.proposal_id}>
                    <td>
                      <strong>{row.server_name || row.server_id}</strong>

                      <small>{row.server_id}</small>
                    </td>

                    <td>
                      <code>{row.action || "—"}</code>
                    </td>

                    <td>
                      <StatusBadge status={row.approval_status || "unknown"} />
                    </td>

                    <td>
                      <StatusBadge
                        status={row.execution_status || "not_executed"}
                      />
                    </td>

                    <td>{row.approver || "—"}</td>

                    <td>{formatTimestamp(row.created_at)}</td>

                    <td>
                      {row.approval_status === "pending_approval" ? (
                        <div className="audit-controls">
                          <button
                            className="approve-button"
                            onClick={() => {
                              setSelectedProposal({
                                proposal_id: row.proposal_id,

                                server_id: row.server_id,

                                server_name: row.server_name,

                                action: row.action,

                                incident_type: row.incident_type,

                                severity: row.severity,

                                approval_status: row.approval_status,

                                execution_status: row.execution_status,
                              });
                            }}
                          >
                            Review
                          </button>
                        </div>
                      ) : (
                        <span className="audit-complete">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {/* ======================================================
          REJECTION MODAL
      ====================================================== */}

      {rejectModal && (
        <div className="modal-overlay">
          <div className="remediation-modal">
            <div className="modal-header">
              <div>
                <span className="eyebrow">POLICY GATE</span>

                <h2>Reject Proposal</h2>
              </div>

              <button
                className="modal-close"
                onClick={() => {
                  setRejectModal(null);
                  setRejectionReason("");
                }}
              >
                ×
              </button>
            </div>

            <div className="modal-proposal">
              <div>
                <span>SERVER</span>

                <strong>
                  {rejectModal.server_name || rejectModal.server_id}
                </strong>
              </div>

              <div>
                <span>ACTION</span>

                <strong>{rejectModal.action || "—"}</strong>
              </div>
            </div>

            <label className="modal-label">Rejection reason</label>

            <textarea
              className="rejection-input"
              value={rejectionReason}
              onChange={(event) => setRejectionReason(event.target.value)}
              placeholder="Explain why this remediation proposal should be rejected..."
              rows={5}
              autoFocus
            />

            <div className="modal-actions">
              <button
                className="secondary-button"
                onClick={() => {
                  setRejectModal(null);
                  setRejectionReason("");
                }}
                disabled={remediationLoading}
              >
                Cancel
              </button>

              <button
                className="reject-button large"
                onClick={rejectProposal}
                disabled={remediationLoading}
              >
                {remediationLoading ? "Rejecting..." : "✕ Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================
   HISTORY
============================================================ */

function HistoryView({
  filteredHistory,
  historyFilter,
  setHistoryFilter,
  incidentHistory,
}) {
  return (
    <div className="view">
      <PageHeading
        eyebrow="AUDIT TRAIL"
        title="Incident History"
        text="Review incident detection, investigation and resolution records."
      />

      <Panel
        title="Historical Incidents"
        eyebrow="POSTGRESQL"
        badge={`${incidentHistory.length} records`}
      >
        <div className="history-toolbar">
          <select
            value={historyFilter}
            onChange={(event) => setHistoryFilter(event.target.value)}
          >
            <option value="all">All incidents</option>

            <option value="active">Active</option>

            <option value="resolved">Resolved</option>

            <option value="investigated">Investigated</option>

            <option value="not-investigated">Not investigated</option>
          </select>
        </div>

        {filteredHistory.length === 0 ? (
          <EmptyState
            icon="✓"
            title="No matching incidents"
            text="No records match the selected filter."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Incident</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Diagnosis</th>
                  <th>Detected</th>
                  <th>Investigated</th>
                  <th>Resolved</th>
                </tr>
              </thead>

              <tbody>
                {filteredHistory.map((incident) => (
                  <tr key={incident.id}>
                    <td>
                      <strong>
                        {incident.server_name || incident.server_id}
                      </strong>

                      <small>{incident.type}</small>

                      <p className="table-message">{incident.message}</p>
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

                    <td>{incident.diagnosis || "Not investigated"}</td>

                    <td>{formatTimestamp(incident.detected_at)}</td>

                    <td>{formatTimestamp(incident.investigated_at)}</td>

                    <td>{formatTimestamp(incident.resolved_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

/* ============================================================
   SETTINGS
============================================================ */

function SettingsView() {
  return (
    <div className="view">
      <PageHeading
        eyebrow="CONFIGURATION"
        title="Settings"
        text="Current CloudOps AI operating configuration."
      />

      <Panel title="Operating Mode" eyebrow="SAFETY">
        <div className="settings-list">
          <SnapshotItem label="AWS Access" value="Read-only" />

          <SnapshotItem label="Investigation" value="LangGraph workflow" />

          <SnapshotItem label="Remediation" value="Approval gated" />

          <SnapshotItem label="Execution" value="Simulation only" />

          <SnapshotItem label="Persistence" value="PostgreSQL" />

          <SnapshotItem label="Refresh" value="30 seconds" />
        </div>
      </Panel>
    </div>
  );
}

/* ============================================================
   SHARED COMPONENTS
============================================================ */

function PageHeading({ eyebrow, title, text }) {
  return (
    <div className="page-heading">
      <span className="eyebrow">{eyebrow}</span>

      <h3>{title}</h3>

      <p>{text}</p>
    </div>
  );
}

function LoadingView({ title, text }) {
  return (
    <div className="view">
      <PageHeading eyebrow="CLOUDOPS AI" title={title} text={text} />

      <Panel>
        <div className="loading-inline">
          <div className="loading-spinner" />
          Loading...
        </div>
      </Panel>
    </div>
  );
}

function Panel({ eyebrow, title, badge, children }) {
  return (
    <section className="panel">
      {(eyebrow || title || badge) && (
        <div className="panel-header">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}

            {title && <h3>{title}</h3>}
          </div>

          {badge && <span className="panel-badge">{badge}</span>}
        </div>
      )}

      {children}
    </section>
  );
}

function MetricCard({ label, value, note, tone = "" }) {
  return (
    <article className="metric-card">
      <span className="metric-label">{label}</span>

      <strong>{value}</strong>

      {note && <small className={tone}>{note}</small>}
    </article>
  );
}

function HealthRow({ icon, tone, label, value }) {
  return (
    <div className="health-row">
      <div>
        <span className={`health-icon ${tone}`}>{icon}</span>

        <span>{label}</span>
      </div>

      <strong>{value}</strong>
    </div>
  );
}

function SnapshotItem({ label, value }) {
  return (
    <div className="snapshot-item">
      <span>{label}</span>

      <strong>{value}</strong>
    </div>
  );
}

function DetailCard({ title, value, emphasis = false }) {
  return (
    <article className={`detail-card ${emphasis ? "emphasis" : ""}`}>
      <span>{title}</span>

      <p>{value}</p>
    </article>
  );
}

function EmptyState({ icon, title, text }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>

      <strong>{title}</strong>

      <p>{text}</p>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = String(status || "unknown")
    .toLowerCase()
    .replace(/\s+/g, "-");

  const labels = {
    connected: "Connected",
    running: "Running",
    stopped: "Stopped",
    error: "Error",
    loading: "Loading",
    healthy: "Healthy",
    warning: "Warning",
    critical: "Critical",
    high: "High",
    medium: "Medium",
    low: "Low",

    pending_approval: "Pending Approval",

    approved: "Approved",

    rejected: "Rejected",

    simulated: "Simulated",

    not_executed: "Not Executed",
  };

  return (
    <span className={`status-badge ${normalized}`}>
      {labels[normalized] || status || "Unknown"}
    </span>
  );
}

function SeverityBadge({ severity }) {
  const normalized = String(severity || "unknown").toLowerCase();

  return <span className={`severity-badge ${normalized}`}>{normalized}</span>;
}

export default App;
