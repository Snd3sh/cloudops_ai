function Sidebar({ activeView, setActiveView }) {
  const navigation = [
    { id: "overview", label: "Overview", icon: "⌂" },
    { id: "monitoring", label: "Monitoring", icon: "◉" },
    { id: "incidents", label: "Incidents", icon: "!" },
    { id: "ai", label: "AI Investigation", icon: "✦" },
    { id: "security", label: "Security", icon: "◇" },
    { id: "cost", label: "Cost", icon: "$" },
    { id: "remediation", label: "Remediation", icon: "⚡" },
    { id: "history", label: "History", icon: "◷" },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">C</div>

        <div>
          <h1>CloudOps</h1>
          <span>AI OPERATIONS</span>
        </div>
      </div>

      <div className="sidebar-section">
        <span className="sidebar-label">WORKSPACE</span>

        <nav className="sidebar-nav">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${
                activeView === item.id ? "active" : ""
              }`}
              onClick={() => setActiveView(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-bottom">
        <button
          className={`nav-item ${
            activeView === "settings" ? "active" : ""
          }`}
          onClick={() => setActiveView("settings")}
        >
          <span className="nav-icon">⚙</span>
          <span>Settings</span>
        </button>

        <div className="sidebar-status">
          <span className="status-dot" />
          <div>
            <strong>System Online</strong>
            <small>CloudOps AI</small>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;