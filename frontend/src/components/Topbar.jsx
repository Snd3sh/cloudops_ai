function Topbar({
  activeView,
  lastUpdated,
  isRefreshing,
  onRefresh,
}) {
  const titles = {
    overview: {
      title: "Overview",
      description: "Cloud infrastructure at a glance",
    },
    monitoring: {
      title: "Monitoring",
      description: "Infrastructure health and resource metrics",
    },
    incidents: {
      title: "Incidents",
      description: "Active and historical infrastructure incidents",
    },
    ai: {
      title: "AI Investigation",
      description: "Multi-agent incident analysis",
    },
    security: {
      title: "Security",
      description: "AWS security findings and exposure analysis",
    },
    cost: {
      title: "Cost Analysis",
      description: "AWS usage and cost insights",
    },
    remediation: {
      title: "Remediation",
      description: "Approval-gated infrastructure actions",
    },
    history: {
      title: "History",
      description: "Incident and remediation audit trail",
    },
    settings: {
      title: "Settings",
      description: "CloudOps AI configuration",
    },
  };

  const current = titles[activeView] || titles.overview;

  return (
    <header className="topbar">
      <div className="topbar-title">
        <h2>{current.title}</h2>
        <p>{current.description}</p>
      </div>

      <div className="topbar-actions">
        <div className="connection-status">
          <span className="status-dot" />
          <span>AWS Connected</span>
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
          <span className={isRefreshing ? "refresh spinning" : "refresh"}>
            ↻
          </span>

          {isRefreshing ? "Refreshing" : "Refresh"}
        </button>
      </div>
    </header>
  );
}

export default Topbar;