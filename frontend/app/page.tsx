'use client';

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell } from 'recharts';

interface TeamStanding {
  team: string;
  expected_points: number;
  expected_gd: number;
  title_prob: number;
  ucl_prob: number;
  relegation_prob: number;
  ai_insight?: string | null;
  positions: Record<string, number>;
}

interface SimulationResponse {
  status: string;
  source: string;
  iterations: number;
  standings: TeamStanding[];
}

export default function Home() {
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [selectedTeam, setSelectedTeam] = useState<TeamStanding | null>(null);
  
  // Slider state
  const [customAtt, setCustomAtt] = useState<number>(0);
  const [customDef, setCustomDef] = useState<number>(0);
  const [simulatingCustom, setSimulatingCustom] = useState<boolean>(false);

  // Natural Language Scenario State
  const [scenarioText, setScenarioText] = useState<string>('');
  const [simulatingNlp, setSimulatingNlp] = useState<boolean>(false);
  const [scenarioReasoning, setScenarioReasoning] = useState<string>('');

  const fetchSimulationData = async (force: boolean = false) => {
    try {
      if (force) setRefreshing(true);
      else setLoading(true);

      const url = `http://127.0.0.1:8000/api/simulate${force ? '?force=true' : ''}`;
      const res = await fetch(url, { cache: 'no-store' });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || `Server returned status ${res.status}`);
      }

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      console.error("Simulation Fetch Error:", err.message);
      alert(`Simulation Error: ${err.message}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Manual Slider Submission
  const runCustomSimulation = async () => {
    if (!selectedTeam) return;
    try {
      setSimulatingCustom(true);
      const payload = {
        overrides: {
          [selectedTeam.team]: {
            att_delta: customAtt,
            def_delta: customDef
          }
        }
      };
      
      const res = await fetch('http://127.0.0.1:8000/api/simulate/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) throw new Error('Custom simulation failed');
      
      const json = await res.json();
      setData(json);
      
      const updatedTeam = json.standings.find((t: TeamStanding) => t.team === selectedTeam.team);
      if (updatedTeam) setSelectedTeam(updatedTeam);
      
    } catch (err: any) {
      console.error(err);
      alert(`Error: ${err.message}`);
    } finally {
      setSimulatingCustom(false);
    }
  };

  // Natural Language Scenario Submission
  const runNlpScenario = async () => {
    if (!selectedTeam || !scenarioText.trim()) return;
    try {
      setSimulatingNlp(true);
      const payload = {
        team: selectedTeam.team,
        scenario: scenarioText
      };

      const res = await fetch('http://127.0.0.1:8000/api/simulate/nlp-scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('AI Scenario evaluation failed');

      const json = await res.json();
      setData(json);

      // Sync slider state & reasoning with AI response
      if (json.ai_deltas) {
        setCustomAtt(json.ai_deltas.att_delta || 0);
        setCustomDef(json.ai_deltas.def_delta || 0);
        setScenarioReasoning(json.ai_deltas.reasoning || '');
      }

      const updatedTeam = json.standings.find((t: TeamStanding) => t.team === selectedTeam.team);
      if (updatedTeam) setSelectedTeam(updatedTeam);

    } catch (err: any) {
      console.error(err);
      alert(`Error: ${err.message}`);
    } finally {
      setSimulatingNlp(false);
    }
  };

  const handleTeamClick = (row: TeamStanding) => {
    setSelectedTeam(row);
    setCustomAtt(0);
    setCustomDef(0);
    setScenarioText('');
    setScenarioReasoning('');
  };

  const downloadCSV = () => {
    if (!data) return;
    const headers = ["Rank", "Club", "Expected Pts", "Expected GD", "Title Prob (%)", "Top 4 Prob (%)", "Relegation Prob (%)", "AI Insight"];
    const rows = data.standings.map((row, index) => [
      index + 1, row.team, row.expected_points.toFixed(1), row.expected_gd.toFixed(1),
      row.title_prob, row.ucl_prob, row.relegation_prob,
      `"${row.ai_insight ? row.ai_insight.replace(/"/g, '""') : 'No AI adjustment'}"`
    ]);
    const csvContent = [headers.join(","), ...rows.map(row => row.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `pl_monte_carlo_sim_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    fetchSimulationData(false);
  }, []);

  if (loading || !data) {
    return (
      <main className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Running Monte Carlo Simulations...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8 relative">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-1">Premier League Predictor</h1>
            <p className="text-gray-400 text-sm">
              Source: <span className={data.source.includes('simulation') ? 'text-indigo-400 font-semibold' : 'text-gray-200'}>{data.source}</span> | Monte Carlo Iterations: {data.iterations}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={downloadCSV}
              disabled={!data || loading || refreshing}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md cursor-pointer"
            >
              📥 Download CSV
            </button>

            <button
              onClick={() => fetchSimulationData(true)}
              disabled={refreshing}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md cursor-pointer"
            >
              {refreshing ? (
                <><div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>Re-simulating...</>
              ) : (
                <>🔄 Reset to Base Engine</>
              )}
            </button>
          </div>
        </div>

        {/* Recharts Visualization */}
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl mb-8 h-96">
          <h2 className="text-xl font-bold mb-6 text-gray-200">Simulated Expected Points</h2>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={data.standings} margin={{ top: 0, right: 10, left: -20, bottom: 60 }}>
              <XAxis dataKey="team" stroke="#9ca3af" tick={{ fontSize: 11 }} interval={0} angle={-45} textAnchor="end" />
              <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} />
              <RechartsTooltip 
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#f3f4f6' }}
                itemStyle={{ color: '#93c5fd', fontWeight: 'bold' }}
                cursor={{ fill: '#374151', opacity: 0.4 }}
              />
              <Bar dataKey="expected_points" name="Expected Points" radius={[4, 4, 0, 0]}>
                {data.standings.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={index < 4 ? '#10b981' : index >= 17 ? '#ef4444' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Dashboard Table */}
        <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700 shadow-xl">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-gray-750 border-b border-gray-700">
                <th className="p-4 font-semibold text-gray-400">Rank</th>
                <th className="p-4 font-semibold text-gray-400">Club</th>
                <th className="p-4 font-semibold text-gray-400">Expected Pts</th>
                <th className="p-4 font-semibold text-gray-400">Exp. GD</th>
                <th className="p-4 font-semibold text-gray-400">Title %</th>
                <th className="p-4 font-semibold text-gray-400">Top 4 %</th>
                <th className="p-4 font-semibold text-gray-400">Rel %</th>
                <th className="p-4 font-semibold text-gray-400">AI Notes</th>
              </tr>
            </thead>
            <tbody>
              {data.standings.map((row, index) => {
                const rank = index + 1;
                let rowColor = "hover:bg-gray-700/50";
                let rankColor = "text-gray-400";
                
                if (rank <= 4) {
                  rowColor = "bg-green-900/10 hover:bg-green-900/20";
                  rankColor = "text-green-400 font-bold";
                } else if (rank >= 18) {
                  rowColor = "bg-red-900/10 hover:bg-red-900/20";
                  rankColor = "text-red-400 font-bold";
                }

                return (
                  <tr 
                    key={row.team} 
                    onClick={() => handleTeamClick(row)}
                    className={`border-b border-gray-700/50 transition-colors cursor-pointer ${rowColor}`}
                  >
                    <td className={`p-4 ${rankColor}`}>{rank}</td>
                    <td className="p-4 font-medium whitespace-nowrap">{row.team}</td>
                    <td className="p-4 text-blue-400 font-bold">{row.expected_points.toFixed(1)}</td>
                    <td className="p-4 text-gray-300 font-medium">
                      {row.expected_gd > 0 ? '+' : ''}{row.expected_gd.toFixed(1)}
                    </td>
                    <td className="p-4 text-gray-300">{row.title_prob > 0 ? `${row.title_prob}%` : '-'}</td>
                    <td className="p-4 text-gray-300">{row.ucl_prob > 0 ? `${row.ucl_prob}%` : '-'}</td>
                    <td className="p-4 text-gray-300">{row.relegation_prob > 0 ? `${row.relegation_prob}%` : '-'}</td>
                    <td className="p-4 text-gray-400 text-xs relative group cursor-help">
                      <div className="max-w-xs truncate">{row.ai_insight ? `✨ ${row.ai_insight}` : ''}</div>
                      {row.ai_insight && (
                        <div className="absolute right-0 top-full mt-1 w-72 p-3 bg-gray-800 text-gray-200 text-xs leading-relaxed rounded-md shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 border border-gray-600 pointer-events-none">
                          <strong className="block text-indigo-400 mb-1">AI Adjustment Reasoning:</strong>
                          {row.ai_insight}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Team Distribution & What-If Modal */}
      {selectedTeam && (
        <div 
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 transition-opacity"
          onClick={() => setSelectedTeam(null)}
        >
          <div 
            className="bg-gray-800 p-6 rounded-xl border border-gray-600 w-full max-w-4xl shadow-2xl overflow-y-auto max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-3xl font-bold text-white mb-1">{selectedTeam.team}</h3>
                <p className="text-gray-400 text-sm mb-2">Monte Carlo Position Distribution</p>
              </div>
              <button 
                onClick={() => setSelectedTeam(null)} 
                className="text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
              >
                ✕
              </button>
            </div>

            {/* AI Natural Language Prompt Section */}
            <div className="bg-gray-700/50 p-5 rounded-lg mb-6 border border-gray-600">
              <h4 className="text-sm font-semibold text-indigo-300 mb-2 uppercase tracking-wider flex items-center gap-2">
                🤖 Describe a Custom Scenario
              </h4>
              <p className="text-xs text-gray-400 mb-3">
                Type any news or hypothetical scenario. AI will evaluate the context and adjust the team multipliers automatically.
              </p>
              <div className="flex gap-3 mb-3">
                <input 
                  type="text" 
                  value={scenarioText}
                  onChange={(e) => setScenarioText(e.target.value)}
                  placeholder={`e.g., ${selectedTeam.team} sign a star forward but lose starting goalkeeper`}
                  className="flex-1 bg-gray-900 border border-gray-600 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={runNlpScenario}
                  disabled={simulatingNlp || !scenarioText.trim()}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 text-white px-4 py-2 rounded-md text-sm font-semibold transition-colors flex items-center gap-2 whitespace-nowrap cursor-pointer"
                >
                  {simulatingNlp ? (
                    <><div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full"></div>Evaluating...</>
                  ) : (
                    '✨ Evaluate with AI'
                  )}
                </button>
              </div>

              {scenarioReasoning && (
                <div className="bg-indigo-950/40 border border-indigo-700/50 rounded-md p-3 text-xs text-indigo-200 mb-4">
                  <strong>AI Assessment:</strong> {scenarioReasoning}
                </div>
              )}

              {/* Manual Override Sliders */}
              <div className="border-t border-gray-600/60 pt-4 mt-2">
                <h5 className="text-xs font-semibold text-gray-300 mb-3 uppercase tracking-wider">
                  🎛️ Manual Multiplier Sliders
                </h5>
                <div className="grid grid-cols-2 gap-8 mb-4">
                  <div>
                    <label className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Attack Multiplier Delta</span>
                      <span className={`font-mono font-bold ${customAtt > 0 ? 'text-green-400' : customAtt < 0 ? 'text-red-400' : 'text-gray-300'}`}>
                        {customAtt > 0 ? '+' : ''}{customAtt.toFixed(1)}
                      </span>
                    </label>
                    <input 
                      type="range" min="-1.0" max="1.0" step="0.1" 
                      value={customAtt} 
                      onChange={(e) => setCustomAtt(parseFloat(e.target.value))}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Defense Multiplier Delta</span>
                      <span className={`font-mono font-bold ${customDef > 0 ? 'text-green-400' : customDef < 0 ? 'text-red-400' : 'text-gray-300'}`}>
                        {customDef > 0 ? '+' : ''}{customDef.toFixed(1)}
                      </span>
                    </label>
                    <input 
                      type="range" min="-1.0" max="1.0" step="0.1" 
                      value={customDef} 
                      onChange={(e) => setCustomDef(parseFloat(e.target.value))}
                      className="w-full accent-indigo-500 cursor-pointer"
                    />
                  </div>
                </div>
                <button 
                  onClick={runCustomSimulation}
                  disabled={simulatingCustom || (customAtt === 0 && customDef === 0)}
                  className="w-full bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 text-white py-2 rounded-md font-semibold text-xs transition-colors shadow-md flex justify-center items-center gap-2 cursor-pointer"
                >
                  {simulatingCustom ? (
                    <><div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full"></div>Applying...</>
                  ) : (
                    'Apply Manual Sliders & Re-Simulate'
                  )}
                </button>
              </div>
            </div>
            
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  data={Object.entries(selectedTeam.positions).map(([pos, prob]) => ({ position: pos, probability: prob }))}
                  margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                >
                  <XAxis dataKey="position" stroke="#9ca3af" tick={{ fontSize: 12 }} label={{ value: 'League Position', position: 'bottom', offset: 0, fill: '#9ca3af', fontSize: 14 }} />
                  <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#f3f4f6' }}
                    itemStyle={{ color: '#93c5fd', fontWeight: 'bold' }}
                    cursor={{ fill: '#374151', opacity: 0.4 }}
                    formatter={(value: any) => [`${value}%`, 'Probability']}
                    labelFormatter={(label) => `Position: ${label}`}
                  />
                  <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
                    {Object.entries(selectedTeam.positions).map(([pos, _], index) => {
                      const positionNum = parseInt(pos);
                      let barColor = "#3b82f6";
                      if (positionNum <= 4) barColor = "#10b981";
                      if (positionNum >= 18) barColor = "#ef4444";
                      return <Cell key={`cell-${index}`} fill={barColor} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}