/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Bell, BellOff, ShieldAlert, CheckCircle, Play, Sparkles, Plus, Clock, Filter, AlertOctagon } from 'lucide-react';

interface AlertRule {
  id: string;
  name: string;
  query: string;
  status: 'firing' | 'pending' | 'ok';
  severity: 'critical' | 'warning' | 'info';
  forTime: string;
  lastEvaluated: string;
}

interface AlertingRulesProps {
  simulationAnomaly: boolean;
  toggleAnomaly: () => void;
  theme: 'light' | 'dark';
}

export default function AlertingRules({ simulationAnomaly, toggleAnomaly, theme }: AlertingRulesProps) {
  const [activeFilter, setActiveFilter] = useState<'all' | 'firing' | 'ok'>('all');

  // Baseline rules
  const baseRules: AlertRule[] = [
    {
      id: 'rule-cpu-spike',
      name: 'System Fleet CPU Usage > 90%',
      query: 'avg by (node) (rate(node_cpu_seconds_total{mode="idle"}[5m])) > 0.90',
      status: simulationAnomaly ? 'firing' : 'ok',
      severity: 'critical',
      forTime: '3m',
      lastEvaluated: new Date().toLocaleTimeString(),
    },
    {
      id: 'rule-error-rate',
      name: 'HTTP Error Rate Threshold Spike',
      query: 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5',
      status: simulationAnomaly ? 'firing' : 'ok',
      severity: 'critical',
      forTime: '2m',
      lastEvaluated: new Date().toLocaleTimeString(),
    },
    {
      id: 'rule-response-latency',
      name: 'P95 API Gateway Response Slowdown',
      query: 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 0.350',
      status: simulationAnomaly ? 'pending' : 'ok',
      severity: 'warning',
      forTime: '5m',
      lastEvaluated: new Date().toLocaleTimeString(),
    },
    {
      id: 'rule-db-replica-lag',
      name: 'Database Cluster Replication Lag',
      query: 'pg_replication_lag_seconds{replica="node-02"} > 30',
      status: 'ok',
      severity: 'warning',
      forTime: '10m',
      lastEvaluated: new Date().toLocaleTimeString(),
    },
    {
      id: 'rule-cache-low-hit',
      name: 'Redis Cache Hit Rate Degradation',
      query: 'redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) < 0.70',
      status: 'ok',
      severity: 'info',
      forTime: '15m',
      lastEvaluated: new Date().toLocaleTimeString(),
    },
  ];

  const filteredRules = baseRules.filter((rule) => {
    if (activeFilter === 'firing') return rule.status === 'firing';
    if (activeFilter === 'ok') return rule.status === 'ok';
    return true;
  });

  const getStatusBadge = (status: 'firing' | 'pending' | 'ok') => {
    switch (status) {
      case 'firing':
        return (
          <span className="inline-flex items-center space-x-1.5 bg-red-500/10 text-red-500 border border-red-500/20 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider animate-pulse">
            <ShieldAlert className="h-3 w-3" />
            <span>Firing</span>
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center space-x-1.5 bg-amber-500/10 text-amber-500 border border-amber-500/20 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider">
            <Clock className="h-3 w-3" />
            <span>Pending</span>
          </span>
        );
      case 'ok':
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider">
            <CheckCircle className="h-3 w-3" />
            <span>Healthy</span>
          </span>
        );
    }
  };

  const getSeverityBadge = (sev: 'critical' | 'warning' | 'info') => {
    switch (sev) {
      case 'critical':
        return <span className="text-[10px] uppercase font-mono font-bold text-red-500 bg-red-100 dark:bg-red-950/45 px-1.5 py-0.5 rounded">Crit</span>;
      case 'warning':
        return <span className="text-[10px] uppercase font-mono font-bold text-amber-500 bg-amber-100 dark:bg-amber-950/45 px-1.5 py-0.5 rounded">Warn</span>;
      case 'info':
      default:
        return <span className="text-[10px] uppercase font-mono font-bold text-[#0066cc] bg-[#0066cc]/10 px-1.5 py-0.5 rounded">Info</span>;
    }
  };

  const cardBg = theme === 'dark' ? 'bg-[#1e2022] border-white/5' : 'bg-white border-[#e0e0e0]';
  const textTitleColor = theme === 'dark' ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = theme === 'dark' ? 'text-white/60' : 'text-[#7a7a7a]';

  return (
    <div className="space-y-6">
      {/* Upper Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className={`text-lg font-semibold tracking-tight ${textTitleColor}`}>
            Grafana Alert Manager (Prometheus engine)
          </h2>
          <p className="text-xs text-[#7a7a7a] mt-0.5">
            Active polling threshold rules on metric aggregates
          </p>
        </div>

        {/* Filter and Trigger Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Segment */}
          <div className={`flex p-0.5 rounded-full ${theme === 'dark' ? 'bg-white/5' : 'bg-black/5'}`}>
            {(['all', 'firing', 'ok'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`px-3 py-1 text-xs rounded-full font-semibold capitalize transition-all ${
                  activeFilter === filter
                    ? 'bg-white text-[#1d1d1f] shadow-sm'
                    : 'text-[#7a7a7a] hover:text-[#1d1d1f]'
                }`}
              >
                {filter === 'all' ? 'All Rules' : filter}
              </button>
            ))}
          </div>

          {/* Test rule trigger */}
          <button
            onClick={toggleAnomaly}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold flex items-center space-x-1.5 border transition-all transform active:scale-95 ${
              simulationAnomaly
                ? 'bg-red-500 text-white border-red-600 hover:bg-red-600 shadow-lg shadow-red-500/20'
                : theme === 'dark' ? 'bg-white/5 border-white/10 text-white hover:bg-white/10' : 'bg-white border-[#e0e0e0] text-[#1d1d1f] hover:bg-black/5'
            }`}
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>{simulationAnomaly ? 'Force Heal' : 'Trigger Alarm Spike'}</span>
          </button>
        </div>
      </div>

      {/* Rules list */}
      <div className="grid grid-cols-1 gap-4">
        {filteredRules.map((rule, idx) => (
          <motion.div
            key={rule.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.05 }}
            className={`border rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 ${cardBg} apple-transition`}
          >
            {/* Left side: Alert description */}
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center space-x-3">
                {getStatusBadge(rule.status)}
                {getSeverityBadge(rule.severity)}
                <h3 className={`text-sm font-semibold tracking-tight ${textTitleColor}`}>
                  {rule.name}
                </h3>
              </div>

              {/* Prometheus query code block */}
              <div className="relative">
                <code className={`block p-3 rounded-lg text-[11px] font-mono whitespace-pre-wrap select-all border ${
                  theme === 'dark' 
                    ? 'bg-[#151617] border-white/5 text-teal-400' 
                    : 'bg-[#fafafc] border-[#f0f0f0] text-[#0066cc]'
                }`}>
                  {rule.query}
                </code>
              </div>

              {/* Alert evaluations metadata */}
              <div className="flex items-center space-x-4 text-[10px] font-mono text-[#7a7a7a]">
                <span>Evaluate interval: every 15s</span>
                <span>For condition duration: {rule.forTime}</span>
                <span>Last updated: {rule.lastEvaluated}</span>
              </div>
            </div>

            {/* Right side: Actions / Dashboard trigger link */}
            <div className="flex items-center space-x-2.5 shrink-0 self-end md:self-center">
              <button className={`px-3 py-1.5 rounded-full text-xs font-semibold border ${
                theme === 'dark' ? 'bg-white/5 border-white/10 hover:bg-white/10 text-white' : 'bg-white border-[#e0e0e0] hover:bg-black/5 text-[#1d1d1f]'
              }`}>
                View dashboard query
              </button>
              <button className="bg-[#0066cc] text-white px-3 py-1.5 rounded-full text-xs font-semibold flex items-center space-x-1 hover:bg-[#0071e3] transition-colors">
                <span>Silence Alert</span>
              </button>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
