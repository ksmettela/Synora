import React, { useState, useEffect } from 'react';
import './App.css';

interface HealthStatus {
  status: string;
  service: string;
  time: string;
}

function App() {
  const [services, setServices] = useState<HealthStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('http://localhost:8084/health');
        const data = await response.json();
        setServices([data]);
      } catch (error) {
        console.error('Error checking health:', error);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Synora Dashboard</h1>
        <p>Audience Correlation & Reporting as a Service</p>
      </header>
      <main>
        <section className="services">
          <h2>Service Status</h2>
          {loading ? (
            <p>Loading...</p>
          ) : (
            <ul>
              {services.map((service) => (
                <li key={service.service}>
                  <span className="status-badge">●</span>
                  <span className="service-name">{service.service}</span>
                  <span className={`status ${service.status}`}>{service.status}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
