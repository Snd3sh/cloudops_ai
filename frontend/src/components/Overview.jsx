function Overview({
  dashboard,
  servers,
  incidents,
  awsData,
}) {
  const running = dashboard?.running_servers ?? 0;
  const stopped = dashboard?.stopped_servers ?? 0;
  const activeIncidents = dashboard?.active_incidents ?? 0;
  const averageCpu = dashboard?.average_cpu ?? 0;

  const critical = dashboard?.critical_incidents ?? 0;
  const high = dashboard?.high_incidents ?? 0;

  return (
    <div className="view">
      <div className="overview-header">
        <div>
          <span className="eyebrow">CLOUD OPERATIONS</span>
          <h3>Infrastructure Overview</h3>
          <p>
            Monitor your cloud environment and investigate issues
            from a single workspace.
          </p>
        </div>

        <div className="environment-badge">
          <span className="status-dot" />
          AWS + Simulation
        </div>
      </div>

      <section className="stats-grid">
        <div className="metric-card">
          <span className="metric-label">TOTAL SERVERS</span>
          <strong>{dashboard?.total_servers ?? 0}</strong>
          <small>Tracked resources</small>
        </div>

        <div className="metric-card">
          <span className="metric-label">RUNNING</span>
          <strong>{running}</strong>
          <small className="positive">Operational</small>
        </div>

        <div className="metric-card">
          <span className="metric-label">OPEN INCIDENTS</span>
          <strong>{activeIncidents}</strong>
          <small className={activeIncidents ? "warning" : "positive"}>
            {activeIncidents ? "Requires attention" : "No active incidents"}
          </small>
        </div>

        <div className="metric-card">
          <span className="metric-label">AVERAGE CPU</span>
          <strong>{averageCpu}%</strong>
          <small>Current workload</small>
        </div>
      </section>

      <section className="overview-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">INFRASTRUCTURE</span>
              <h3>System Health</h3>
            </div>

            <span className="panel-badge">
              {servers.length} resources
            </span>
          </div>

          <div className="health-list">
            <div className="health-row">
              <div>
                <span className="health-icon healthy">✓</span>
                <span>Running servers</span>
              </div>

              <strong>{running}</strong>
            </div>

            <div className="health-row">
              <div>
                <span className="health-icon stopped">!</span>
                <span>Stopped servers</span>
              </div>

              <strong>{stopped}</strong>
            </div>

            <div className="health-row">
              <div>
                <span className="health-icon warning">!</span>
                <span>High severity incidents</span>
              </div>

              <strong>{high}</strong>
            </div>

            <div className="health-row">
              <div>
                <span className="health-icon critical">!</span>
                <span>Critical incidents</span>
              </div>

              <strong>{critical}</strong>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">INCIDENT CENTER</span>
              <h3>Active Incidents</h3>
            </div>

            <span className="panel-badge danger">
              {incidents.length}
            </span>
          </div>

          {incidents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">✓</div>
              <strong>No active incidents</strong>
              <p>Your monitored environment is currently healthy.</p>
            </div>
          ) : (
            <div className="incident-preview">
              {incidents.slice(0, 4).map((incident) => (
                <div
                  className="incident-row"
                  key={incident.id || incident.server_id}
                >
                  <div>
                    <strong>{incident.server_name}</strong>
                    <span>{incident.type}</span>
                  </div>

                  <span
                    className={`severity ${incident.severity}`}
                  >
                    {incident.severity}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel aws-summary">
        <div className="panel-header">
          <div>
            <span className="eyebrow">AWS</span>
            <h3>Cloud Resources</h3>
          </div>

          <span className="panel-badge">
            {awsData?.instances?.length ?? 0} EC2
          </span>
        </div>

        <div className="aws-summary-grid">
          <div>
            <span>Region</span>
            <strong>
              {awsData?.region || "eu-central-1"}
            </strong>
          </div>

          <div>
            <span>Instances</span>
            <strong>
              {awsData?.total_instances ?? 0}
            </strong>
          </div>

          <div>
            <span>Data source</span>
            <strong>Read-only</strong>
          </div>

          <div>
            <span>Environment</span>
            <strong>Development</strong>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Overview;