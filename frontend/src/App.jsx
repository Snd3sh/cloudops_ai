
import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [servers, setServers] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [awsData, setAwsData] = useState(null);
  const [error, setError] = useState("");
  const [awsError, setAwsError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        const [dashboardRes, monitoringRes, incidentsRes] =
          await Promise.all([
            fetch(`${API_URL}/api/dashboard`),
            fetch(`${API_URL}/api/monitoring`),
            fetch(`${API_URL}/api/incidents`),
          ]);

        if (
          !dashboardRes.ok ||
          !monitoringRes.ok ||
          !incidentsRes.ok
        ) {
          throw new Error("Failed to fetch monitoring data");
        }

        const [dashboardData, monitoringData, incidentsData] =
          await Promise.all([
            dashboardRes.json(),
            monitoringRes.json(),
            incidentsRes.json(),
          ]);

        if (isMounted) {
          setDashboard(dashboardData);
          setServers(monitoringData.servers);
          setIncidents(incidentsData.incidents);
          setError("");
        }
      } catch {
        if (isMounted) {
          setError(
            "Unable to fetch dashboard data. Check whether FastAPI is running."
          );
        }
      }

      // AWS data is loaded separately so an AWS error
      // doesn't hide the simulated dashboard.
      try {
        const response = await fetch(
          `${API_URL}/api/aws/instances`
        );

        if (!response.ok) {
          throw new Error("AWS request failed");
        }

        const data = await response.json();

        if (isMounted) {
          setAwsData(data);
          setAwsError("");
        }
      } catch {
        if (isMounted) {
          setAwsError(
            "Unable to load AWS instances. Check AWS credentials, permissions, and backend logs."
          );
        }
      }
    }

    loadData();

    const intervalId = setInterval(loadData, 10000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  if (error) {
    return (
      <main className="app">
        <h1>CloudOps AI</h1>
        <p className="error">{error}</p>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className="app">
        <h1>CloudOps AI</h1>
        <p>Loading dashboard...</p>
      </main>
    );
  }

  return (
    <main className="app">
      <header className="header">
        <div>
          <p className="eyebrow">CLOUD OPERATIONS PLATFORM</p>
          <h1>CloudOps AI</h1>
          <p className="subtitle">
            Monitor resources and identify infrastructure incidents.
          </p>
        </div>

        <span className="source-badge">
          AWS + SIMULATION
        </span>
      </header>

      <section className="stats">
        <StatCard
          title="Simulated Servers"
          value={dashboard.total_servers}
        />
        <StatCard
          title="Running"
          value={dashboard.running_servers}
        />
        <StatCard
          title="Stopped"
          value={dashboard.stopped_servers}
        />
        <StatCard
          title="Open Incidents"
          value={dashboard.total_incidents}
        />
      </section>

      <section className="panel">
        <h2>Real AWS EC2 Instances</h2>

        {awsError ? (
          <p className="error">{awsError}</p>
        ) : !awsData ? (
          <p>Loading AWS resources...</p>
        ) : (
          <>
            <div className="aws-summary">
              <p>
                <strong>Region:</strong> {awsData.region}
              </p>
              <p>
                <strong>Total instances:</strong>{" "}
                {awsData.total_instances}
              </p>
              <span className="source-badge">LIVE AWS API</span>
            </div>

            {awsData.instances.length === 0 ? (
              <p>
                No EC2 instances found in this region.
                This is normal if you haven't launched any.
              </p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Instance Name</th>
                      <th>Instance ID</th>
                      <th>Type</th>
                      <th>Region</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {awsData.instances.map((instance) => (
                      <tr key={instance.id}>
                        <td>
                          <strong>{instance.name}</strong>
                        </td>
                        <td>{instance.id}</td>
                        <td>{instance.instance_type}</td>
                        <td>{instance.region}</td>
                        <td>
                          <span
                            className={`status ${instance.status}`}
                          >
                            {instance.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <section className="panel">
        <h2>Simulated Server Monitoring</h2>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Server</th>
                <th>Region</th>
                <th>Status</th>
                <th>CPU Usage</th>
              </tr>
            </thead>
            <tbody>
              {servers.map((server) => (
                <tr key={server.id}>
                  <td>
                    <strong>{server.name}</strong>
                    <small>{server.id}</small>
                  </td>
                  <td>{server.region}</td>
                  <td>
                    <span className={`status ${server.status}`}>
                      {server.status}
                    </span>
                  </td>
                  <td>
                    <div className="cpu-cell">
                      <div className="cpu-track">
                        <div
                          className={`cpu-fill ${
                            server.cpu_usage > 80 ? "high" : ""
                          }`}
                          style={{
                            width: `${server.cpu_usage}%`,
                          }}
                        />
                      </div>
                      <span>{server.cpu_usage}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h2>Detected Incidents</h2>

        {incidents.length === 0 ? (
          <p>No incidents detected.</p>
        ) : (
          <div className="incident-list">
            {incidents.map((incident, index) => (
              <article
                className="incident"
                key={`${incident.server_id}-${incident.type}-${index}`}
              >
                <div>
                  <strong>{incident.server_name}</strong>
                  <p>{incident.message}</p>
                  <small>{incident.type}</small>
                </div>

                <span className={`severity ${incident.severity}`}>
                  {incident.severity}
                </span>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer>
        CloudOps AI · AWS read-only monitoring ·
        Simulated incident detection
      </footer>
    </main>
  );
}

function StatCard({ title, value }) {
  return (
    <article className="stat-card">
      <p>{title}</p>
      <strong>{value}</strong>
    </article>
  );
}

export default App;