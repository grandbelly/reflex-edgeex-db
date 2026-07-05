/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Activity, Cpu, ShieldAlert, Wifi, Globe, Clock } from 'lucide-react';

interface GlobalNavProps {
  simulationAnomaly: boolean;
}

export default function GlobalNav({ simulationAnomaly }: GlobalNavProps) {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('ko-KR', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav
      id="apple-global-nav"
      className="w-full h-11 bg-[#000000] text-white flex items-center justify-between px-4 sm:px-8 select-none z-50 relative border-b border-white/10"
    >
      {/* Left: Brand logo & Indicator */}
      <div className="flex items-center space-x-3">
        <Activity className="h-4.5 w-4.5 text-[#0066cc]" />
        <span className="font-sans text-xs tracking-tight font-semibold text-white/90">
          Grafana Premium Benchmark
        </span>
        <div className="hidden sm:flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-white/10 text-[10px] text-white/80">
          <span className={`h-1.5 w-1.5 rounded-full ${simulationAnomaly ? 'bg-red-500 animate-pulse' : 'bg-green-400'}`} />
          <span>{simulationAnomaly ? 'ANOMALY ALERT' : 'SYSTEM OPTIMAL'}</span>
        </div>
      </div>

      {/* Middle: Minimal Navigation Links (Aesthetic only as per Apple Design) */}
      <div className="hidden md:flex items-center space-x-6 text-[11px] font-sans text-white/60 tracking-normal">
        <span className="hover:text-white/90 cursor-pointer transition-colors">Server Cluster</span>
        <span className="hover:text-white/90 cursor-pointer transition-colors">Metrics Engine</span>
        <span className="hover:text-white/90 cursor-pointer transition-colors">Alert rules</span>
        <span className="hover:text-white/90 cursor-pointer transition-colors">Integrations</span>
      </div>

      {/* Right: Telemetry metadata */}
      <div className="flex items-center space-x-4 text-xs font-mono text-white/50">
        <div className="hidden sm:flex items-center space-x-1">
          <Globe className="h-3.5 w-3.5" />
          <span>Seoul Node-A</span>
        </div>
        <div className="flex items-center space-x-1.5 text-white/70">
          <Clock className="h-3.5 w-3.5 text-white/40" />
          <span className="tracking-widest">{time || '00:00:00'}</span>
        </div>
      </div>
    </nav>
  );
}
