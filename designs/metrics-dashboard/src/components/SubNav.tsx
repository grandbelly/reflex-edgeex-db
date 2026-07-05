/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Play, Pause, AlertOctagon, RefreshCw, Layers, Cpu, Terminal, Grid3X3 } from 'lucide-react';
import { TimeRange } from '../types';

interface SubNavProps {
  activeTab: 'overview' | 'metrics' | 'logs' | 'topology';
  setActiveTab: (tab: 'overview' | 'metrics' | 'logs' | 'topology') => void;
  timeRange: TimeRange;
  setTimeRange: (range: TimeRange) => void;
  isLive: boolean;
  setIsLive: (live: boolean) => void;
  simulationAnomaly: boolean;
  toggleAnomaly: () => void;
  onManualRefresh: () => void;
}

export default function SubNav({
  activeTab,
  setActiveTab,
  timeRange,
  setTimeRange,
  isLive,
  setIsLive,
  simulationAnomaly,
  toggleAnomaly,
  onManualRefresh,
}: SubNavProps) {
  return (
    <div
      id="apple-sub-nav"
      className="sticky top-0 w-full h-[52px] bg-[#f5f5f7]/85 backdrop-blur-md z-40 border-b border-[#e0e0e0] flex items-center justify-between px-4 sm:px-8 select-none"
    >
      {/* Left: Dashboard identity */}
      <div className="flex items-center space-x-3">
        <h1 className="font-sans font-semibold text-lg sm:text-[21px] tracking-tight text-[#1d1d1f]">
          System Node Explorer
        </h1>
        <span className="hidden sm:inline-block h-3.5 w-[1px] bg-[#e0e0e0]" />
        <span className="hidden sm:inline-block text-xs text-[#7a7a7a] font-medium tracking-wide">
          v2.4.0-Production
        </span>
      </div>

      {/* Center: Tabs & Segment controls */}
      <div className="flex items-center space-x-1 sm:space-x-2">
        <div className="flex bg-[#e0e0e0]/50 p-0.5 rounded-full">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1 text-xs rounded-full font-medium flex items-center space-x-1.5 transition-all duration-200 ${
              activeTab === 'overview'
                ? 'bg-white text-[#1d1d1f] shadow-sm'
                : 'text-[#7a7a7a] hover:text-[#1d1d1f]'
            }`}
          >
            <Layers className="h-3 w-3" />
            <span className="hidden md:inline">Overview</span>
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-3 py-1 text-xs rounded-full font-medium flex items-center space-x-1.5 transition-all duration-200 ${
              activeTab === 'metrics'
                ? 'bg-white text-[#1d1d1f] shadow-sm'
                : 'text-[#7a7a7a] hover:text-[#1d1d1f]'
            }`}
          >
            <Cpu className="h-3 w-3" />
            <span className="hidden md:inline">Metrics Explorer</span>
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`px-3 py-1 text-xs rounded-full font-medium flex items-center space-x-1.5 transition-all duration-200 ${
              activeTab === 'logs'
                ? 'bg-white text-[#1d1d1f] shadow-sm'
                : 'text-[#7a7a7a] hover:text-[#1d1d1f]'
            }`}
          >
            <Terminal className="h-3 w-3" />
            <span className="hidden md:inline">Event Logs</span>
          </button>
          <button
            onClick={() => setActiveTab('topology')}
            className={`px-3 py-1 text-xs rounded-full font-medium flex items-center space-x-1.5 transition-all duration-200 ${
              activeTab === 'topology'
                ? 'bg-white text-[#1d1d1f] shadow-sm'
                : 'text-[#7a7a7a] hover:text-[#1d1d1f]'
            }`}
          >
            <Grid3X3 className="h-3 w-3" />
            <span className="hidden md:inline">Fleet Nodes</span>
          </button>
        </div>
      </div>

      {/* Right: Controls (Anomaly Trigger, Time scale, Live Switch) */}
      <div className="flex items-center space-x-1.5 sm:space-x-3">
        {/* Manual Refresh (when not live) */}
        {!isLive && (
          <button
            onClick={onManualRefresh}
            title="Manual sync"
            className="p-1.5 rounded-full hover:bg-black/5 text-[#1d1d1f] transition-all"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        )}

        {/* Time Range selector */}
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          className="bg-transparent border-0 text-xs font-semibold text-[#1d1d1f] focus:ring-0 cursor-pointer outline-none hover:text-[#0066cc] py-1 transition-colors"
        >
          <option value="15m">Last 15 Minutes</option>
          <option value="1h">Last 1 Hour</option>
          <option value="24h">Last 24 Hours</option>
        </select>

        {/* Live stream Toggler */}
        <button
          onClick={() => setIsLive(!isLive)}
          className={`flex items-center space-x-1 px-2.5 py-1 text-xs rounded-full font-medium border transition-all ${
            isLive
              ? 'bg-[#0066cc]/10 border-[#0066cc] text-[#0066cc]'
              : 'bg-white border-[#e0e0e0] text-[#7a7a7a] hover:text-[#1d1d1f]'
          }`}
        >
          {isLive ? <Play className="h-3 w-3 fill-current animate-pulse" /> : <Pause className="h-3 w-3" />}
          <span className="text-[11px] font-semibold">{isLive ? 'LIVE STREAM' : 'STREAM OFF'}</span>
        </button>

        {/* Anomaly trigger - Action Blue Pill layout, customized with warning action */}
        <button
          onClick={toggleAnomaly}
          className={`px-3 py-1.5 text-xs rounded-full font-semibold flex items-center space-x-1 border shadow-xs transform active:scale-[0.95] transition-all ${
            simulationAnomaly
              ? 'bg-red-500 border-red-600 text-white hover:bg-red-600'
              : 'bg-white border-[#e0e0e0] text-[#1d1d1f] hover:border-red-400 hover:text-red-500'
          }`}
        >
          <AlertOctagon className={`h-3.5 w-3.5 ${simulationAnomaly ? 'animate-bounce' : ''}`} />
          <span className="hidden sm:inline">
            {simulationAnomaly ? 'Resolve Anomaly' : 'Simulate Spike'}
          </span>
        </button>
      </div>
    </div>
  );
}
