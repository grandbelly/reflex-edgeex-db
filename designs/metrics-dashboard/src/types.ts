/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface MetricPoint {
  timestamp: string; // ISO string or short time
  rawTime: number;   // Epoch ms
  cpu: number;       // percentage
  memory: number;    // percentage
  requestRate: number; // req/sec
  responseTime: number; // ms
  errorRate: number; // percentage
  dbLatency: number; // ms
  activeSessions: number;
  cacheHitRate: number; // percentage
  networkIn: number; // MB/s
  networkOut: number; // MB/s
}

export type LogLevel = 'info' | 'warn' | 'error' | 'success';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  service: string;
  duration?: number;
}

export interface ServerStatus {
  id: string;
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  cpu: number;
  memory: number;
  activeSessions: number;
  region: string;
  uptime: string;
}

export type TimeRange = '15m' | '1h' | '24h';

export interface DashboardFilter {
  timeRange: TimeRange;
  selectedNode: string; // 'all' or specific node id
  isLive: boolean;
  activeTab: 'overview' | 'metrics' | 'logs' | 'topology';
  simulationAnomaly: boolean;
}
