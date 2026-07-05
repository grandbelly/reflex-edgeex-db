/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { motion } from 'motion/react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend, BarChart, Bar } from 'recharts';
import { MetricPoint } from '../types';
import { Server, ArrowUp, ArrowDown } from 'lucide-react';

interface AnalyticsChartsProps {
  history: MetricPoint[];
  simulationAnomaly: boolean;
  theme?: 'light' | 'dark';
}

export default function AnalyticsCharts({ history, simulationAnomaly, theme = 'dark' }: AnalyticsChartsProps) {
  // Use last 40 data points to make the charts breathable and high-density
  const activeData = history.slice(-40);

  const isDark = theme === 'dark';
  const cardBg = isDark ? 'bg-[#1e2022] border-white/5' : 'bg-white border-[#e0e0e0] shadow-sm';
  const textColor = isDark ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = isDark ? 'text-white/40' : 'text-[#7a7a7a]';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : '#f0f0f0';
  const borderDivider = isDark ? 'border-white/5' : 'border-[#f0f0f0]';
  const axisColor = isDark ? 'rgba(255,255,255,0.3)' : 'rgba(29,29,31,0.45)';

  // Custom tooltips to retain the pristine Apple design
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className={`p-3 rounded-lg shadow-xl font-sans text-xs border ${
          isDark ? 'bg-[#18191b] border-white/10 text-white' : 'bg-white text-[#1d1d1f] border-[#e0e0e0]'
        }`}>
          <p className={`font-mono mb-1.5 ${isDark ? 'text-[#7a7a7a]' : 'text-[#86868b]'}`}>{label}</p>
          <div className="space-y-1">
            {payload.map((item: any) => (
              <div key={item.name} className="flex items-center justify-between space-x-4">
                <span className="flex items-center space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className={isDark ? 'text-white/80' : 'text-[#1d1d1f]/80'}>{item.name}</span>
                </span>
                <span className={`font-mono font-semibold ${isDark ? 'text-white' : 'text-[#1d1d1f]'}`}>
                  {item.value.toLocaleString()}
                  {item.unit || ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {/* Chart 1: Time Series Traffic & Query Latency (Area + Line) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className={`lg:col-span-2 border rounded-[18px] p-6 flex flex-col justify-between min-h-[380px] ${cardBg} apple-transition`}
      >
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className={`text-base font-semibold tracking-tight ${textColor}`}>
                Traffic Request Volume & DB Latency
              </h3>
              <p className="text-xs text-[#7a7a7a] mt-0.5">
                Real-time ingestion and storage replication throughput
              </p>
            </div>
            {simulationAnomaly && (
              <span className="text-[10px] bg-red-500/10 text-red-500 border border-red-500/20 px-2 py-0.5 rounded-full font-bold animate-pulse">
                SPIKE ALERT
              </span>
            )}
          </div>

          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isDark ? '#2997ff' : '#0066cc'} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={isDark ? '#2997ff' : '#0066cc'} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis
                  dataKey="timestamp"
                  stroke={axisColor}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                />
                <YAxis
                  yAxisId="left"
                  stroke={axisColor}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  axisLine={false}
                  dx={-5}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke={axisColor}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  axisLine={false}
                  dx={5}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  yAxisId="left"
                  type="monotone"
                  name="Requests"
                  dataKey="requestRate"
                  stroke={isDark ? '#2997ff' : '#0066cc'}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRequests)"
                  unit=" req/s"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  name="DB Latency"
                  dataKey="dbLatency"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={false}
                  unit=" ms"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={`flex items-center space-x-6 text-xs text-[#7a7a7a] mt-2 border-t pt-3 ${borderDivider}`}>
          <div className="flex items-center space-x-2">
            <span className={`w-2.5 h-2.5 rounded-full ${isDark ? 'bg-[#2997ff]' : 'bg-[#0066cc]'}`} />
            <span className={`font-medium ${textColor}`}>HTTP Ingestion Rate</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#a855f7]" />
            <span className={`font-medium ${textColor}`}>SQL Query latency</span>
          </div>
        </div>
      </motion.div>

      {/* Chart 2: Resource Exhaustion Level (Stacked Bar) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className={`border rounded-[18px] p-6 flex flex-col justify-between min-h-[380px] ${cardBg} apple-transition`}
      >
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className={`text-base font-semibold tracking-tight ${textColor}`}>
                Server Networking Bandwidth
              </h3>
              <p className="text-xs text-[#7a7a7a] mt-0.5">
                Total throughput inbound vs outbound nodes
              </p>
            </div>
            <Server className={`h-4 w-4 ${textMuted}`} />
          </div>

          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={activeData} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
                <XAxis
                  dataKey="timestamp"
                  stroke={axisColor}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                />
                <YAxis
                  stroke={axisColor}
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  tickLine={false}
                  axisLine={false}
                  dx={-5}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  name="Network In"
                  dataKey="networkIn"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  unit=" MB/s"
                />
                <Line
                  type="monotone"
                  name="Network Out"
                  dataKey="networkOut"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  unit=" MB/s"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Dynamic metadata summary footer for Network */}
        <div className={`mt-4 border-t pt-4 grid grid-cols-2 gap-4 ${borderDivider}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-xs text-[#7a7a7a]">
              <ArrowDown className="h-3.5 w-3.5 text-[#10b981]" />
              <span>Inbound Max</span>
            </div>
            <span className={`text-xs font-semibold font-mono ${textColor}`}>
              {Math.max(...activeData.map((d) => d.networkIn)).toFixed(1)} MB/s
            </span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-xs text-[#7a7a7a]">
              <ArrowUp className="h-3.5 w-3.5 text-[#f59e0b]" />
              <span>Outbound Max</span>
            </div>
            <span className={`text-xs font-semibold font-mono ${textColor}`}>
              {Math.max(...activeData.map((d) => d.networkOut)).toFixed(1)} MB/s
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
