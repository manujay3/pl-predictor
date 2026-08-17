"use client";

import { useState, useEffect } from "react";

interface Fixture {
  home_team: string;
  away_team: string;
  home_xg: number;
  away_xg: number;
  home_win_pct: number;
  draw_pct: number;
  away_win_pct: number;
  projected_score: string;
}

export default function FixturesTable({ teamFilter = "" }: { teamFilter?: string }) {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFixtures = async () => {
      setLoading(true);
      // Append the team query parameter if a specific team is selected
      const url = teamFilter 
        ? `http://127.0.0.1:8000/api/fixtures?team=${encodeURIComponent(teamFilter)}`
        : `http://127.0.0.1:8000/api/fixtures`;
        
      try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.status === "success") {
          setFixtures(data.fixtures);
        }
      } catch (err) {
        console.error("Error fetching fixtures:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchFixtures();
  }, [teamFilter]);

  if (loading) {
    return <div className="p-4 text-gray-400 animate-pulse">Simulating 380 match odds...</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-700 shadow-lg mt-6">
      <table className="min-w-full text-sm text-left text-gray-300">
        <thead className="text-xs uppercase bg-slate-800/50 border-b border-slate-700">
          <tr>
            <th className="px-4 py-4 font-semibold">Matchup</th>
            <th className="px-4 py-4 text-center font-semibold">Proj. Score</th>
            <th className="px-4 py-4 text-center font-semibold">Home Win %</th>
            <th className="px-4 py-4 text-center font-semibold">Draw %</th>
            <th className="px-4 py-4 text-center font-semibold">Away Win %</th>
            <th className="px-4 py-4 text-center font-semibold">Expected Goals</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-700/50 bg-slate-900/50">
          {fixtures.map((f, idx) => (
            <tr key={idx} className="hover:bg-slate-800 transition-colors">
              <td className="px-4 py-3 font-medium">
                {f.home_team} <span className="text-slate-500 mx-2">vs</span> {f.away_team}
              </td>
              <td className="px-4 py-3 text-center font-bold text-blue-400">
                {f.projected_score}
              </td>
              <td className="px-4 py-3 text-center text-emerald-400">{f.home_win_pct}%</td>
              <td className="px-4 py-3 text-center text-slate-400">{f.draw_pct}%</td>
              <td className="px-4 py-3 text-center text-rose-400">{f.away_win_pct}%</td>
              <td className="px-4 py-3 text-center text-slate-400 text-xs">
                {f.home_xg.toFixed(2)} - {f.away_xg.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}