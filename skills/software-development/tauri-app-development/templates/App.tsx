import { createRoot } from 'react-dom/client';

function App() {
  return (
    <div style={{
      fontFamily: 'system-ui, -apple-system, sans-serif',
      background: '#0F172A',
      color: '#F8FAFC',
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚀 MyApp</h1>
        <p style={{ fontSize: '1.25rem', color: '#94A3B8' }}>
          Tauri + React + TypeScript
        </p>
        <p style={{ marginTop: '2rem', color: '#64748B' }}>
          v0.1.0 - Development Build
        </p>
      </div>
    </div>
  );
}

const container = document.getElementById('root');
const root = createRoot(container!);
root.render(<App />);
