/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { motion } from 'motion/react';
import { Cpu, Database, Activity, Clock, ShieldAlert, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { MetricPoint } from '../types';

interface MetricsCardsProps {
  currentMetrics: MetricPoint;
  history: MetricPoint[];
  simulationAnomaly: boolean;
  theme?: 'light' | 'dark';
}

interface CardConfig {
  title: string;
  value: string | number;
  unit: string;
  icon: React.ElementType;
  dataKey: keyof MetricPoint;
  color: string;
  bgColor: string;
  borderColor: string;
  desc: string;
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
}

export default function MetricsCards({ currentMetrics, history, simulationAnomaly, theme = 'dark' }: MetricsCardsProps) {
  // Extract sparkline data (last 20 points for brevity)
  const sparklineData = history.slice(-20);

  // Calculate trends vs previous point
  const getTrend = (key: keyof MetricPoint): { type: 'up' | 'down' | 'neutral'; val: string } => {
    if (history.length < 2) return { type: 'neutral', val: '0%' };
    const prev = history[history.length - 2][key] as number;
    const curr = currentMetrics[key] as number;
    if (prev === 0) return { type: 'neutral', val: '0%' };
    
    const diff = curr - prev;
    const percent = ((diff / prev) * 100).toFixed(1);
    
    if (diff > 0.1) return { type: 'up', val: `+${percent}%` };
    if (diff < -0.1) return { type: 'down', val: `${percent}%` };
    return { type: 'neutral', val: '0.0%' };
  };

  const isDark = theme === 'dark';
  const defaultBorder = isDark ? 'border-white/5' : 'border-[#e0e0e0]';

  const cards: CardConfig[] = [
    {
      title: 'CPU Usage',
      value: currentMetrics.cpu.toFixed(1),
      unit: '%',
      icon: Cpu,
      dataKey: 'cpu',
      color: simulationAnomaly ? '#ef4444' : '#2997ff',
      bgColor: isDark ? 'bg-[#1e2022]' : 'bg-white',
      borderColor: simulationAnomaly ? 'border-red-500/50' : defaultBorder,
      desc: 'Active system core allocation',
      trend: getTrend('cpu').type,
      trendValue: getTrend('cpu').val,
    },
    {
      title: 'Memory load',
      value: currentMetrics.memory.toFixed(1),
      unit: '%',
      icon: Database,
      dataKey: 'memory',
      color: '#a855f7', // Purple
      bgColor: isDark ? 'bg-[#1e2022]' : 'bg-white',
      borderColor: defaultBorder,
      desc: 'RAM buffer space utilized',
      trend: getTrend('memory').type,
      trendValue: getTrend('memory').val,
    },
    {
      title: 'Request Rate',
      value: currentMetrics.requestRate.toLocaleString(),
      unit: 'req/s',
      icon: Activity,
      dataKey: 'requestRate',
      color: '#10b981', // Emerald
      bgColor: isDark ? 'bg-[#1e2022]' : 'bg-white',
      borderColor: defaultBorder,
      desc: 'Incoming HTTP packet density',
      trend: getTrend('requestRate').type,
      trendValue: getTrend('requestRate').val,
    },
    {
      title: 'Response Latency',
      value: currentMetrics.responseTime,
      unit: 'ms',
      icon: Clock,
      dataKey: 'responseTime',
      color: simulationAnomaly ? '#f59e0b' : '#2997ff', // Amber or Action Blue
      bgColor: isDark ? 'bg-[#1e2022]' : 'bg-white',
      borderColor: simulationAnomaly ? 'border-amber-500/50' : defaultBorder,
      desc: 'P95 request turnaround duration',
      trend: getTrend('responseTime').type,
      trendValue: getTrend('responseTime').val,
    },
    {
      title: 'HTTP Error Rate',
      value: currentMetrics.errorRate.toFixed(2),
      unit: '%',
      icon: ShieldAlert,
      dataKey: 'errorRate',
      color: currentMetrics.errorRate > 2.0 ? '#ef4444' : '#10b981',
      bgColor: currentMetrics.errorRate > 2.0 ? (isDark ? 'bg-red-950/20' : 'bg-red-50/50') : (isDark ? 'bg-[#1e2022]' : 'bg-white'),
      borderColor: currentMetrics.errorRate > 2.0 ? (isDark ? 'border-red-900/30' : 'border-red-200') : defaultBorder,
      desc: 'Failed requests / total density',
      trend: getTrend('errorRate').type,
      trendValue: getTrend('errorRate').val,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        const isSpiked = simulationAnomaly && (card.dataKey === 'cpu' || card.dataKey === 'responseTime' || card.dataKey === 'errorRate');

        return (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.05 }}
            className={`apple-transition relative rounded-[18px] border ${card.borderColor} ${card.bgColor} p-5 flex flex-col justify-between overflow-hidden h-[185px]`}
            style={{
              boxShadow: isSpiked ? 'rgba(239, 68, 68, 0.1) 0px 10px 30px' : 'none'
            }}
          >
            {/* Top Row: Meta info */}
            <div>
              <div className={`flex items-center justify-between mb-2 ${isDark ? 'text-white/40' : 'text-[#7a7a7a]'}`}>
                <span className="text-[11px] font-bold tracking-tight uppercase font-mono">
                  {card.title}
                </span>
                <Icon className="h-4 w-4 opacity-80" style={{ color: card.color }} />
              </div>

              {/* Main value display */}
              <div className="flex items-baseline space-x-1">
                <span className={`text-[34px] font-semibold tracking-tight font-sans leading-none ${
                  isSpiked 
                    ? 'text-red-500 font-bold' 
                    : isDark ? 'text-white' : 'text-[#1d1d1f]'
                }`}>
                  {card.value}
                </span>
                <span className={`text-xs font-semibold ${isDark ? 'text-white/40' : 'text-[#7a7a7a]'}`}>{card.unit}</span>
              </div>
            </div>

            {/* Middle Row: Trend & mini sparkline */}
            <div className="mt-2 flex items-center justify-between z-10">
              {/* Trend Badge */}
              <div className="flex items-center space-x-1">
                {card.trend === 'up' && (
                  <ArrowUpRight className={`h-3.5 w-3.5 ${card.dataKey === 'errorRate' || card.dataKey === 'responseTime' ? 'text-red-500' : 'text-emerald-500'}`} />
                )}
                {card.trend === 'down' && (
                  <ArrowDownRight className={`h-3.5 w-3.5 ${card.dataKey === 'errorRate' || card.dataKey === 'responseTime' ? 'text-emerald-500' : 'text-red-500'}`} />
                )}
                <span
                  className={`text-xs font-semibold ${
                    card.trend === 'neutral'
                      ? isDark ? 'text-white/40' : 'text-[#7a7a7a]'
                      : card.trend === 'up'
                      ? card.dataKey === 'errorRate' || card.dataKey === 'responseTime'
                        ? 'text-red-500'
                        : 'text-emerald-500'
                      : card.dataKey === 'errorRate' || card.dataKey === 'responseTime'
                      ? 'text-emerald-500'
                      : 'text-red-500'
                  }`}
                >
                  {card.trendValue}
                </span>
              </div>

              <span className={`text-[10px] font-mono truncate max-w-[110px] ${isDark ? 'text-white/30' : 'text-[#7a7a7a]'}`}>
                {card.desc}
              </span>
            </div>

            {/* Bottom Sparkline (Pure Apple-esque minimalism - absolute positioned at bottom) */}
            <div className="absolute bottom-0 left-0 right-0 h-11 opacity-40 select-none pointer-events-none">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={sparklineData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`gradient-${card.dataKey}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={card.color} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={card.color} stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey={card.dataKey}
                    stroke={card.color}
                    strokeWidth={1.5}
                    fill={`url(#gradient-${card.dataKey})`}
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
