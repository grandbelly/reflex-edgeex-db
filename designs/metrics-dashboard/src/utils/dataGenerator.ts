/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { MetricPoint, LogEntry, ServerStatus, TimeRange } from '../types';

// Standard helper for random values with bounds
const randomRange = (min: number, max: number) => {
  return Math.random() * (max - min) + min;
};

// Generate initial metrics based on time range
export const generateMetricsData = (range: TimeRange, hasAnomaly: boolean): MetricPoint[] => {
  const points = 60;
  const data: MetricPoint[] = [];
  const now = Date.now();
  
  let intervalMs = 15000; // Default 15s for 15m
  if (range === '1h') {
    intervalMs = 60000; // 1m for 1h
  } else if (range === '24h') {
    intervalMs = 1440000; // 24m for 24h
  }

  for (let i = points - 1; i >= 0; i--) {
    const time = now - i * intervalMs;
    const dateObj = new Date(time);
    
    // Time format depending on range
    let timeStr = '';
    if (range === '15m') {
      timeStr = dateObj.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } else if (range === '1h') {
      timeStr = dateObj.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit' });
    } else {
      timeStr = `${dateObj.getMonth() + 1}/${dateObj.getDate()} ${dateObj.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit' })}`;
    }

    // Base noise and sinusoidal fluctuations
    const wave = Math.sin((points - i) / 5) * 10;
    const baseCpu = 40 + wave + randomRange(-5, 5);
    const baseMemory = 68 + Math.cos((points - i) / 8) * 4 + randomRange(-1, 1);
    const baseRequest = 250 + Math.sin((points - i) / 3) * 50 + randomRange(-15, 15);
    const baseResponse = 120 + Math.cos((points - i) / 4) * 30 + randomRange(-10, 10);
    const baseError = randomRange(0, 1.5) > 1.3 ? randomRange(1.5, 4.0) : randomRange(0.1, 0.9);

    // Create a spike for some parts if Anomaly is active
    const isAnomalyZone = hasAnomaly && i < 15; // Last 15 data points are spiked
    
    data.push({
      timestamp: timeStr,
      rawTime: time,
      cpu: Math.min(100, Math.max(0, isAnomalyZone ? randomRange(88, 98) : baseCpu)),
      memory: Math.min(100, Math.max(0, isAnomalyZone ? randomRange(85, 94) : baseMemory)),
      requestRate: Math.max(0, Math.round(isAnomalyZone ? baseRequest * 1.8 + randomRange(-30, 50) : baseRequest)),
      responseTime: Math.max(10, Math.round(isAnomalyZone ? baseResponse * 4.5 + randomRange(-100, 200) : baseResponse)),
      errorRate: Math.max(0, parseFloat((isAnomalyZone ? randomRange(12, 28) : baseError).toFixed(2))),
      dbLatency: Math.max(2, Math.round(isAnomalyZone ? randomRange(80, 160) : randomRange(12, 35))),
      activeSessions: Math.round(isAnomalyZone ? 1420 + randomRange(-100, 150) : 850 + Math.sin((points - i) / 6) * 100 + randomRange(-20, 20)),
      cacheHitRate: parseFloat((isAnomalyZone ? randomRange(52, 68) : randomRange(91, 98.8)).toFixed(1)),
      networkIn: parseFloat((isAnomalyZone ? randomRange(45, 68) : randomRange(12, 25)).toFixed(1)),
      networkOut: parseFloat((isAnomalyZone ? randomRange(95, 140) : randomRange(35, 60)).toFixed(1)),
    });
  }

  return data;
};

// Generate next point for live updates
export const generateNextPoint = (prevData: MetricPoint[], hasAnomaly: boolean): MetricPoint => {
  const lastPoint = prevData[prevData.length - 1];
  const nextTime = lastPoint.rawTime + 15000; // Assumes 15s updates for live
  const dateObj = new Date(nextTime);
  const timeStr = dateObj.toLocaleTimeString('ko-KR', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

  // Generate smooth transition
  const baseCpu = 40 + Math.sin(nextTime / 50000) * 8 + randomRange(-4, 4);
  const baseMemory = lastPoint.memory + randomRange(-0.5, 0.5);
  const baseRequest = 250 + Math.sin(nextTime / 30000) * 40 + randomRange(-10, 10);
  const baseResponse = 120 + Math.cos(nextTime / 40000) * 20 + randomRange(-8, 8);
  const baseError = randomRange(0, 1) > 0.85 ? randomRange(1.2, 3.5) : randomRange(0.1, 0.7);

  return {
    timestamp: timeStr,
    rawTime: nextTime,
    cpu: Math.min(100, Math.max(0, hasAnomaly ? randomRange(91, 99) : baseCpu)),
    memory: Math.min(100, Math.max(0, hasAnomaly ? randomRange(88, 95) : baseMemory)),
    requestRate: Math.max(0, Math.round(hasAnomaly ? baseRequest * 1.9 + randomRange(-20, 40) : baseRequest)),
    responseTime: Math.max(10, Math.round(hasAnomaly ? baseResponse * 5.2 + randomRange(-50, 150) : baseResponse)),
    errorRate: Math.max(0, parseFloat((hasAnomaly ? randomRange(15, 29) : baseError).toFixed(2))),
    dbLatency: Math.max(2, Math.round(hasAnomaly ? randomRange(95, 170) : randomRange(15, 32))),
    activeSessions: Math.round(hasAnomaly ? 1520 + randomRange(-80, 120) : 850 + Math.sin(nextTime / 60000) * 90 + randomRange(-15, 15)),
    cacheHitRate: parseFloat((hasAnomaly ? randomRange(50, 65) : randomRange(92, 98.5)).toFixed(1)),
    networkIn: parseFloat((hasAnomaly ? randomRange(48, 70) : randomRange(14, 26)).toFixed(1)),
    networkOut: parseFloat((hasAnomaly ? randomRange(100, 145) : randomRange(38, 62)).toFixed(1)),
  };
};

// Initial system logs list
export const generateInitialLogs = (): LogEntry[] => {
  const services = ['auth-service', 'gateway', 'payment-api', 'user-db', 'cache-node-01', 'frontend-edge'];
  const logTemplates = [
    { level: 'info', message: 'HTTP Request GET /api/v1/user/profile succeeded', service: 'gateway', duration: 12 },
    { level: 'info', message: 'Connection established with database cluster UserDB-Primary', service: 'user-db' },
    { level: 'success', message: 'Successfully preheated Cache segment #09 in 142ms', service: 'cache-node-01', duration: 142 },
    { level: 'info', message: 'Token token_66a89f verified for user_id=99281', service: 'auth-service', duration: 4 },
    { level: 'info', message: 'Bento UI theme context loaded successfully', service: 'frontend-edge' },
    { level: 'warn', message: 'Database query slow-log: SELECT * FROM transaction WHERE status = ? LIMIT 100', service: 'user-db', duration: 245 },
    { level: 'info', message: 'Asset compression algorithm gzip ratio: 3.4x', service: 'frontend-edge' },
    { level: 'success', message: 'API validation passed for POST /api/v2/payment/charge', service: 'payment-api', duration: 48 },
    { level: 'info', message: 'Heartbeat signal broadcasted to node fleet (8/8 healthy)', service: 'gateway' },
  ];

  const logs: LogEntry[] = [];
  const now = Date.now();

  for (let i = 0; i < 40; i++) {
    const timeOffset = i * randomRange(4000, 15000);
    const logTime = new Date(now - timeOffset);
    const template = logTemplates[Math.floor(Math.random() * logTemplates.length)];
    const id = `log-${now - timeOffset}-${i}`;

    logs.push({
      id,
      timestamp: logTime.toISOString(),
      level: template.level as any,
      message: template.message,
      service: template.service,
      duration: template.duration,
    });
  }

  return logs;
};

// Generate a random log stream item
export const generateRandomLog = (hasAnomaly: boolean): LogEntry => {
  const services = ['gateway', 'auth-service', 'payment-api', 'user-db', 'cache-node-01', 'frontend-edge'];
  const infoLogs = [
    'HTTP GET /api/v1/analytics/overview - 200 OK',
    'HTTP POST /api/v1/settings - 200 OK',
    'Cache hit for key user:session:981223',
    'Nginx proxy buffer chunk recycled',
    'Cron-job scheduler: sync-invoice status finished',
    'Websocket handshake initiated on channel #global',
  ];
  const warnLogs = [
    'Connection pool utilization reached 78% (39/50)',
    'Redis storage warning: high fragment ratio detected',
    'API response threshold limit exceeded on auth-service',
    'Garbage collection major sweep completed: reclaimed 114MB',
  ];
  const errorLogs = [
    'Database connection timeout for node UserDB-Replica-02',
    'HTTP POST /api/v2/payment/charge - 504 Gateway Timeout',
    'Internal Server Error: failed to serialize response payload',
    'Deadlock detected in Transaction table, query retrying',
    'Out of Memory panic averted by automatic worker swap',
  ];
  const successLogs = [
    'Database migration schema_v14 applied successfully',
    'Payment ledger integrity verification passed',
    'SSL certificate renewal checklist succeeded',
    'Microservice routing table sync completed',
  ];

  const now = Date.now();
  const id = `log-${now}-${Math.floor(Math.random() * 1000)}`;
  let level: LogEntry['level'] = 'info';
  let message = '';
  let service = services[Math.floor(Math.random() * services.length)];
  let duration = randomRange(1, 25);

  if (hasAnomaly) {
    // 60% chance of errors during anomaly
    const roll = Math.random();
    if (roll < 0.6) {
      level = 'error';
      message = errorLogs[Math.floor(Math.random() * errorLogs.length)];
      duration = randomRange(500, 2500);
    } else if (roll < 0.8) {
      level = 'warn';
      message = warnLogs[Math.floor(Math.random() * warnLogs.length)];
      duration = randomRange(200, 600);
    } else {
      level = 'info';
      message = 'HTTP GET /api/v1/status - 503 Service Unavailable';
      duration = randomRange(400, 1200);
    }
  } else {
    // Normal traffic mix
    const roll = Math.random();
    if (roll < 0.7) {
      level = 'info';
      message = infoLogs[Math.floor(Math.random() * infoLogs.length)];
    } else if (roll < 0.85) {
      level = 'success';
      message = successLogs[Math.floor(Math.random() * successLogs.length)];
      duration = randomRange(10, 50);
    } else if (roll < 0.95) {
      level = 'warn';
      message = warnLogs[Math.floor(Math.random() * warnLogs.length)];
      duration = randomRange(100, 300);
    } else {
      level = 'error';
      message = errorLogs[Math.floor(Math.random() * errorLogs.length)];
      duration = randomRange(300, 800);
    }
  }

  return {
    id,
    timestamp: new Date(now).toISOString(),
    level,
    message,
    service,
    duration: Math.round(duration),
  };
};

// Server status node list
export const generateServerStatus = (): ServerStatus[] => {
  return [
    { id: 'node-ap-east-1', name: 'ap-east-01.pod.infra', status: 'healthy', cpu: 32, memory: 72, activeSessions: 382, region: 'Asia Pacific (Hong Kong)', uptime: '48d 12h' },
    { id: 'node-ap-east-2', name: 'ap-east-02.pod.infra', status: 'healthy', cpu: 41, memory: 68, activeSessions: 420, region: 'Asia Pacific (Hong Kong)', uptime: '48d 12h' },
    { id: 'node-us-west-1', name: 'us-west-01.pod.infra', status: 'healthy', cpu: 28, memory: 61, activeSessions: 245, region: 'US West (Oregon)', uptime: '124d 4h' },
    { id: 'node-us-east-1', name: 'us-east-01.pod.infra', status: 'healthy', cpu: 55, memory: 81, activeSessions: 512, region: 'US East (N. Virginia)', uptime: '9d 18h' },
    { id: 'node-eu-central-1', name: 'eu-cent-01.pod.infra', status: 'healthy', cpu: 19, memory: 54, activeSessions: 188, region: 'Europe (Frankfurt)', uptime: '213d 1h' },
    { id: 'node-db-primary', name: 'db-master-primary.infra', status: 'healthy', cpu: 45, memory: 88, activeSessions: 94, region: 'Asia Pacific (Hong Kong)', uptime: '320d 9h' },
    { id: 'node-cache-cluster', name: 'redis-cluster-sharded', status: 'healthy', cpu: 12, memory: 91, activeSessions: 1205, region: 'Multi-Region (VPC)', uptime: '542d 11h' },
  ];
};
