/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Database, Link2, Wifi, Search, Play, Plus, Activity, Terminal, Cloud } from 'lucide-react';

interface DataSource {
  id: string;
  name: string;
  type: string;
  url: string;
  status: 'connected' | 'degraded' | 'disconnected';
  icon: React.ElementType;
  lastPing: string;
}

interface ConnectionsProps {
  theme: 'light' | 'dark';
}

export default function Connections({ theme }: ConnectionsProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');

  const datasources: DataSource[] = [
    { id: 'ds-prom', name: 'Prometheus-Seoul-Cluster', type: 'TimeSeries Metric', url: 'http://prometheus.production.vpc:9090', status: 'connected', icon: Activity, lastPing: '4ms' },
    { id: 'ds-loki', name: 'Grafana Loki Central Logs', type: 'Structured Log Ingest', url: 'http://loki.internal.dns:3100', status: 'connected', icon: Terminal, lastPing: '12ms' },
    { id: 'ds-postgres', name: 'UserDB PostgreSQL Master', type: 'Relational Database', url: 'postgresql://db-primary.cloudsql:5432', status: 'connected', icon: Database, lastPing: '8ms' },
    { id: 'ds-jaeger', name: 'Jaeger Distributed Traces', type: 'Distributed APM Traces', url: 'http://jaeger-collector.internal:14268', status: 'connected', icon: Link2, lastPing: '19ms' },
    { id: 'ds-cloudwatch', name: 'AWS CloudWatch Gateway', type: 'Multi-Cloud Collector', url: 'aws://cloudwatch.ap-northeast-2', status: 'degraded', icon: Cloud, lastPing: '142ms' },
  ];

  const filtered = datasources.filter(ds => 
    ds.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    ds.type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusBadge = (status: DataSource['status']) => {
    switch (status) {
      case 'connected':
        return (
          <span className="inline-flex items-center space-x-1 text-emerald-500 font-bold text-[10px] uppercase font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Online</span>
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center space-x-1 text-amber-500 font-bold text-[10px] uppercase font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            <span>Degraded</span>
          </span>
        );
      case 'disconnected':
      default:
        return (
          <span className="inline-flex items-center space-x-1 text-red-500 font-bold text-[10px] uppercase font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
            <span>Offline</span>
          </span>
        );
    }
  };

  const cardBg = theme === 'dark' ? 'bg-[#1e2022] border-white/5' : 'bg-white border-[#e0e0e0]';
  const textTitleColor = theme === 'dark' ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = theme === 'dark' ? 'text-white/60' : 'text-[#7a7a7a]';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className={`text-lg font-semibold tracking-tight ${textTitleColor}`}>
            Active Data Sources & Integrations
          </h2>
          <p className="text-xs text-[#7a7a7a] mt-0.5">
            Manage physical cluster connections feeding into the visualization panels
          </p>
        </div>

        {/* Add Connection CTA */}
        <button className="bg-[#0066cc] text-white px-4 py-2 rounded-full text-xs font-semibold flex items-center space-x-1.5 hover:bg-[#0071e3] transition-colors shadow-xs transform active:scale-95">
          <Plus className="w-4 h-4" />
          <span>Configure New Data Source</span>
        </button>
      </div>

      {/* Search Filter */}
      <div className="relative">
        <Search className={`absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 ${theme === 'dark' ? 'text-white/30' : 'text-black/30'}`} />
        <input 
          type="text" 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search endpoints, connection protocols, or database names..."
          className={`w-full py-2.5 pl-10 pr-4 text-xs font-mono rounded-full border outline-none apple-transition ${
            theme === 'dark' 
              ? 'bg-[#1d1d1f] border-white/10 text-white focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc]' 
              : 'bg-[#f5f5f7] border-[#e0e0e0] text-[#1d1d1f] focus:bg-white focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc]'
          }`}
        />
      </div>

      {/* List of datasources */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((ds, idx) => {
          const Icon = ds.icon;
          return (
            <motion.div
              key={ds.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.04 }}
              className={`border rounded-2xl p-5 flex flex-col justify-between h-[180px] ${cardBg} hover:border-[#0066cc]/50 apple-transition`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 bg-[#0066cc]/10 rounded-lg text-[#0066cc]">
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  {getStatusBadge(ds.status)}
                </div>

                <div>
                  <h3 className={`text-sm font-semibold tracking-tight ${textTitleColor}`}>
                    {ds.name}
                  </h3>
                  <p className="text-[11px] text-[#7a7a7a] mt-0.5 uppercase tracking-wider font-mono">
                    {ds.type}
                  </p>
                </div>
              </div>

              {/* Ping information & Link button */}
              <div className="flex items-center justify-between border-t border-[#f0f0f0] dark:border-white/5 pt-3 text-[10px] font-mono text-[#7a7a7a]">
                <div className="flex flex-col">
                  <span>Latency: <strong className="font-semibold text-emerald-500">{ds.lastPing}</strong></span>
                  <span className="truncate max-w-[150px]">{ds.url}</span>
                </div>
                <button className={`px-2.5 py-1 rounded-md text-[10px] font-semibold border ${
                  theme === 'dark' ? 'bg-white/5 border-white/10 text-white' : 'bg-white border-[#e0e0e0] text-[#1d1d1f]'
                }`}>
                  Test ping
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
