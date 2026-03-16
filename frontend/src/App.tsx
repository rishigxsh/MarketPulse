import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-tight text-white">
            MarketPulse
          </h1>
          <span className="text-xs text-gray-500">Real-Time Stock & Crypto Dashboard</span>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-6">
        <Dashboard />
      </main>
    </div>
  );
}
