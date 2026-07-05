/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Server, CheckCircle, AlertTriangle, AlertCircle, RefreshCw, Activity, ArrowRight, ArrowUpRight } from 'lucide-react';
import { ServerStatus } from '../types';

interface TopologyGridProps {
  servers: ServerStatus[];
  simulationAnomaly: boolean;
  onRefresh: () => void;
  theme?: 'light' | 'dark';
}

export default function TopologyGrid({ servers, simulationAnomaly, onRefresh, theme = 'dark' }: TopologyGridProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const isDark = theme === 'dark';
  const textColor = isDark ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = isDark ? 'text-white/40' : 'text-[#7a7a7a]';
  const borderDivider = isDark ? 'border-white/5' : 'border-[#f0f0f0]';
  const sidebarBg = isDark ? 'bg-[#1e2022] border-white/5' : 'bg-white border-[#e0e0e0]';

  // If anomaly is active, we simulate that some key servers degrade
  const getSimulatedStatus = (srv: ServerStatus) => {
    if (!simulationAnomaly) return srv;
    
    // Speculate degradation during anomaly
    if (srv.id === 'node-db-primary') {
      return { ...srv, status: 'critical' as const, cpu: 94, memory: 92, activeSessions: 142 };
    }
    if (srv.id === 'node-ap-east-1' || srv.id === 'node-us-east-1') {
      return { ...srv, status: 'warning' as const, cpu: 89, memory: 86, activeSessions: srv.activeSessions * 1.5 };
    }
    return srv;
  };

  const getStatusIcon = (status: 'healthy' | 'warning' | 'critical') => {
    switch (status) {
      case 'critical':
        return <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />;
      case 'healthy':
      default:
        return <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />;
    }
  };

  const getStatusClass = (status: 'healthy' | 'warning' | 'critical') => {
    switch (status) {
      case 'critical':
        return isDark ? 'border-red-950/45 bg-red-950/20 text-red-400' : 'border-red-200 bg-red-50/50';
      case 'warning':
        return isDark ? 'border-amber-950/45 bg-amber-950/20 text-amber-400' : 'border-amber-200 bg-amber-50/30';
      case 'healthy':
      default:
        return isDark ? 'border-white/5 bg-[#1e2022]' : 'border-[#e0e0e0] bg-white';
    }
  };

  const activeServers = servers.map(getSimulatedStatus);
  const selectedServer = activeServers.find((s) => s.id === selectedNodeId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
      {/* Node Grid Cluster (LHS) */}
      <div className="lg:col-span-3 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-4 select-none">
            <div>
              <h3 className={`text-base font-semibold tracking-tight ${textColor}`}>
                Cluster Fleet Node Topology
              </h3>
              <p className="text-xs text-[#7a7a7a] mt-0.5">
                Physical node availability and routing segments
              </p>
            </div>
            
            <button
              onClick={onRefresh}
              className={`p-1.5 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-all ${textColor}`}
              title="Recalibrate fleet"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {activeServers.map((server, idx) => {
              const isSelected = selectedNodeId === server.id;
              
              return (
                <motion.div
                  key={server.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.04 }}
                  onClick={() => setSelectedNodeId(isSelected ? null : server.id)}
                  className={`apple-transition cursor-pointer border rounded-[18px] p-4 flex flex-col justify-between h-[135px] ${getStatusClass(
                    server.status
                  )} ${isSelected ? 'ring-2 ring-[#0066cc] border-transparent' : 'hover:border-[#7a7a7a]'}`}
                >
                  {/* Top line: Node details */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="p-1.5 bg-black/5 dark:bg-white/5 rounded-md">
                        <Server className={`h-4 w-4 ${textColor}`} />
                      </div>
                      <div>
                        <p className={`text-xs font-semibold tracking-tight truncate max-w-[120px] ${textColor}`}>
                          {server.name}
                        </p>
                        <p className={`text-[10px] font-mono ${textMuted}`}>{server.region}</p>
                      </div>
                    </div>
                    {getStatusIcon(server.status)}
                  </div>

                  {/* Midline: Metrics overview */}
                  <div className={`grid grid-cols-2 gap-2 text-center border-t pt-2 mt-2 ${borderDivider}`}>
                    <div>
                      <span className="block text-[9px] font-mono text-[#7a7a7a] uppercase">CPU Load</span>
                      <span className={`text-xs font-semibold font-mono ${textColor}`}>{server.cpu}%</span>
                    </div>
                    <div>
                      <span className="block text-[9px] font-mono text-[#7a7a7a] uppercase">Mem Buffer</span>
                      <span className={`text-xs font-semibold font-mono ${textColor}`}>{server.memory}%</span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Node Analysis Side Drawer Card (RHS) */}
      <div className="lg:col-span-1">
        <AnimatePresence mode="wait">
          {selectedServer ? (
            <motion.div
              key={selectedServer.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className={`border rounded-[18px] p-5 h-full flex flex-col justify-between ${sidebarBg} apple-transition`}
            >
              <div>
                <div className={`flex items-center justify-between border-b pb-3 mb-4 select-none ${borderDivider}`}>
                  <h4 className="text-xs font-bold tracking-wider text-[#7a7a7a] uppercase">
                    Node Diagnostic
                  </h4>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${isDark ? 'bg-white/5 text-teal-400' : 'bg-black/5 text-[#1d1d1f]'}`}>
                    Active
                  </span>
                </div>

                <div className="space-y-4">
                  {/* Title block */}
                  <div>
                    <h5 className={`text-[15px] font-bold truncate ${textColor}`}>
                      {selectedServer.name}
                    </h5>
                    <p className="text-xs text-[#7a7a7a] mt-0.5">{selectedServer.region}</p>
                  </div>

                  {/* Hardware levels with elegant bars */}
                  <div className="space-y-2.5">
                    {/* CPU gauge */}
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1">
                        <span className="text-[#7a7a7a]">CPU Allocation</span>
                        <span className={`font-semibold ${textColor}`}>{selectedServer.cpu}%</span>
                      </div>
                      <div className={`w-full h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-white/10' : 'bg-[#f0f0f0]'}`}>
                        <div
                          className={`h-full rounded-full ${
                            selectedServer.cpu > 85 ? 'bg-red-500' : 'bg-[#0066cc]'
                          }`}
                          style={{ width: `${selectedServer.cpu}%` }}
                        />
                      </div>
                    </div>

                    {/* Memory gauge */}
                    <div>
                      <div className="flex justify-between text-xs font-mono mb-1">
                        <span className="text-[#7a7a7a]">Memory Commit</span>
                        <span className={`font-semibold ${textColor}`}>{selectedServer.memory}%</span>
                      </div>
                      <div className={`w-full h-1.5 rounded-full overflow-hidden ${isDark ? 'bg-white/10' : 'bg-[#f0f0f0]'}`}>
                        <div
                          className="h-full bg-purple-500 rounded-full"
                          style={{ width: `${selectedServer.memory}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Meta Key-value values */}
                  <div className={`border-t pt-4 space-y-2 text-xs font-mono ${borderDivider}`}>
                    <div className="flex justify-between">
                      <span className="text-[#7a7a7a]">Uptime Counter:</span>
                      <span className={`font-semibold ${textColor}`}>{selectedServer.uptime}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#7a7a7a]">Session count:</span>
                      <span className={`font-semibold ${textColor}`}>
                        {selectedServer.activeSessions.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#7a7a7a]">Status tier:</span>
                      <span className={`capitalize font-bold ${
                        selectedServer.status === 'critical'
                          ? 'text-red-500'
                          : selectedServer.status === 'warning'
                          ? 'text-amber-500'
                          : 'text-emerald-500'
                      }`}>
                        {selectedServer.status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action pill in card */}
              <button className="w-full bg-[#0066cc] text-white py-2.5 rounded-full text-xs font-semibold flex items-center justify-center space-x-1.5 shadow-sm transform active:scale-[0.95] hover:bg-[#0071e3] transition-all mt-4">
                <span>View Full Telemetry Trace</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </button>
            </motion.div>
          ) : (
            <div className={`border-2 border-dashed rounded-[18px] p-6 h-full flex flex-col items-center justify-center text-center text-[#7a7a7a] select-none min-h-[220px] ${
              isDark ? 'border-white/10 bg-white/2' : 'border-[#e0e0e0] bg-dashed'
            }`}>
              <Server className="h-8 w-8 opacity-40 mb-2 stroke-[1.25]" />
              <p className="text-xs font-medium">Select any node card to analyze hardware trace logs</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
