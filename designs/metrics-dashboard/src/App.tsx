/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ShieldAlert, 
  Plus, 
  Star, 
  Share2, 
  Settings, 
  ChevronDown, 
  Sun, 
  Moon, 
  HelpCircle,
  TrendingUp,
  Database,
  Search,
  Activity,
  Terminal,
  Server,
  Layers,
  Sparkles,
  RefreshCw
} from 'lucide-react';

import GrafanaSidebar from './components/GrafanaSidebar';
import MetricsCards from './components/MetricsCards';
import AnalyticsCharts from './components/AnalyticsCharts';
import LogViewer from './components/LogViewer';
import TopologyGrid from './components/TopologyGrid';
import AlertingRules from './components/AlertingRules';
import Connections from './components/Connections';

import { MetricPoint, LogEntry, ServerStatus, TimeRange } from './types';
import { generateMetricsData, generateNextPoint, generateInitialLogs, generateRandomLog, generateServerStatus } from './utils/dataGenerator';

interface CustomPanel {
  id: string;
  title: string;
  query: string;
  metric: 'cpu' | 'memory' | 'requestRate' | 'responseTime';
  chartType: 'area' | 'bar';
}

export default function App() {
  // Theme state: light or dark (Apple aesthetics)
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Grafana Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [activeView, setActiveView] = useState<'overview' | 'explore' | 'alerting' | 'connections' | 'fleet' | 'variables' | 'settings'>('overview');

  // Grafana Variables Selector
  const [selectedDS, setSelectedDS] = useState<string>('Prometheus-Seoul');
  const [selectedEnv, setSelectedEnv] = useState<string>('production');
  const [selectedNode, setSelectedNode] = useState<string>('all');

  // Core configurations
  const [timeRange, setTimeRange] = useState<TimeRange>('15m');
  const [isLive, setIsLive] = useState<boolean>(true);
  const [simulationAnomaly, setSimulationAnomaly] = useState<boolean>(false);
  const [isStarred, setIsStarred] = useState<boolean>(false);

  // Core monitoring datasets
  const [metricsHistory, setMetricsHistory] = useState<MetricPoint[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [servers, setServers] = useState<ServerStatus[]>([]);

  // Grafana Custom Panels Creator
  const [customPanels, setCustomPanels] = useState<CustomPanel[]>([]);
  const [showAddPanel, setShowAddPanel] = useState<boolean>(false);
  const [newPanelTitle, setNewPanelTitle] = useState<string>('');
  const [newPanelQuery, setNewPanelQuery] = useState<string>('');
  const [newPanelMetric, setNewPanelMetric] = useState<'cpu' | 'memory' | 'requestRate' | 'responseTime'>('cpu');

  // State initialization
  useEffect(() => {
    const initialMetrics = generateMetricsData(timeRange, simulationAnomaly);
    setMetricsHistory(initialMetrics);
    setLogs(generateInitialLogs());
    setServers(generateServerStatus());
  }, [timeRange]);

  // Handle manual data refresh
  const handleManualRefresh = () => {
    const refreshedMetrics = generateMetricsData(timeRange, simulationAnomaly);
    setMetricsHistory(refreshedMetrics);
    
    // Add a manual trigger log
    const syncLog: LogEntry = {
      id: `manual-sync-${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: 'success',
      service: 'gateway',
      message: 'Manual telemetric sync invoked: fleet nodes recalibrated successfully.',
      duration: 82
    };
    setLogs(prev => [...prev, syncLog]);
  };

  // Live Simulation Thread (Ingest metrics & logs every 1.8 seconds)
  useEffect(() => {
    if (!isLive) return;

    const timer = setInterval(() => {
      // 1. Append next telemetry data point
      setMetricsHistory((prev) => {
        const nextPoint = generateNextPoint(prev, simulationAnomaly);
        return [...prev.slice(1), nextPoint];
      });

      // 2. Append new dynamic log entries
      setLogs((prev) => {
        const newLog = generateRandomLog(simulationAnomaly);
        if (simulationAnomaly && Math.random() > 0.4) {
          const extraLog1 = generateRandomLog(true);
          const extraLog2 = generateRandomLog(true);
          return [...prev, newLog, extraLog1, extraLog2].slice(-150);
        }
        return [...prev, newLog].slice(-150);
      });
    }, 1800);

    return () => clearInterval(timer);
  }, [isLive, simulationAnomaly]);

  // Handle anomaly state
  const toggleAnomalyState = () => {
    const nextState = !simulationAnomaly;
    setSimulationAnomaly(nextState);

    const triggerLog: LogEntry = {
      id: `anomaly-state-${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: nextState ? 'error' : 'success',
      service: 'gateway',
      message: nextState 
        ? 'ALERT BRAKE: Simulated database load spikes triggered across primary master node.' 
        : 'RECOVERY RESOLUTION: Simulated database spikes cleared. Scaling factors returned to threshold.',
      duration: nextState ? 450 : 210
    };
    setLogs(prev => [...prev, triggerLog]);
  };

  const handleResolveAnomaly = () => {
    setSimulationAnomaly(false);
    const resolutionLog: LogEntry = {
      id: `anomaly-resolved-${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: 'success',
      service: 'gateway',
      message: 'SYSTEM MITIGATION TRIGGERED: Cluster core throttle scaled up, traffic balanced.',
      duration: 1120
    };
    setLogs(prev => [...prev, resolutionLog]);
  };

  // Create new Custom Panel
  const handleCreatePanel = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPanelTitle.trim()) return;

    const newPanel: CustomPanel = {
      id: `panel-${Date.now()}`,
      title: newPanelTitle,
      query: newPanelQuery || `avg(rate(cluster_metric{name="${newPanelMetric}"}[5m]))`,
      metric: newPanelMetric,
      chartType: 'area',
    };

    setCustomPanels([...customPanels, newPanel]);
    setNewPanelTitle('');
    setNewPanelQuery('');
    setShowAddPanel(false);

    // Emit connection success log
    const panelLog: LogEntry = {
      id: `panel-creation-${Date.now()}`,
      timestamp: new Date().toISOString(),
      level: 'success',
      service: 'dashboard-engine',
      message: `Successfully provisioned custom panel "${newPanel.title}" executing query [${newPanel.query}].`,
      duration: 140
    };
    setLogs(prev => [...prev, panelLog]);
  };

  const currentMetrics = metricsHistory[metricsHistory.length - 1] || {
    cpu: 0,
    memory: 0,
    requestRate: 0,
    responseTime: 0,
    errorRate: 0,
    dbLatency: 0,
    activeSessions: 0,
    cacheHitRate: 0,
    networkIn: 0,
    networkOut: 0,
  };

  // Theme styling presets matching Apple design token overrides
  const pageBg = theme === 'dark' ? 'bg-[#111214]' : 'bg-[#f5f5f7]';
  const cardBg = theme === 'dark' ? 'bg-[#18191b] border-white/5 shadow-2xl' : 'bg-white border-[#e0e0e0]';
  const textColor = theme === 'dark' ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = theme === 'dark' ? 'text-white/60' : 'text-[#7a7a7a]';
  const headerBg = theme === 'dark' ? 'bg-[#18191b] border-white/5' : 'bg-[#fafafc] border-[#e0e0e0]';
  const selectionColor = theme === 'dark' ? 'selection:bg-[#0066cc]/40 selection:text-[#2997ff]' : 'selection:bg-[#0066cc]/20 selection:text-[#0066cc]';

  return (
    <div className={`min-h-screen flex h-screen overflow-hidden ${pageBg} ${textColor} ${selectionColor}`}>
      
      {/* 1. Grafana-style Sidebar Left Section */}
      <GrafanaSidebar 
        isOpen={sidebarOpen} 
        setIsOpen={setSidebarOpen} 
        activeView={activeView as any} 
        setActiveView={(v) => setActiveView(v as any)} 
        theme={theme}
      />

      {/* Main Content Area Right Section */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        
        {/* 2. Top Navigation Header (Breadcrumbs, Variable Selectors, Settings) */}
        <header className={`h-14 shrink-0 flex items-center justify-between px-6 border-b ${headerBg} select-none`}>
          
          {/* Breadcrumbs (Grafana style) */}
          <div className="flex items-center space-x-2 text-xs">
            <span className={textMuted}>Dashboards</span>
            <span className={textMuted}>/</span>
            <span className={textMuted}>Seoul Production</span>
            <span className={textMuted}>/</span>
            <div className="flex items-center space-x-1 font-semibold text-inherit">
              <span>Overview Node Cluster</span>
              <button 
                onClick={() => setIsStarred(!isStarred)} 
                className={`p-1 rounded-full transition-colors ${
                  isStarred ? 'text-[#ffb800]' : `${textMuted} hover:text-[#ffb800]`
                }`}
              >
                <Star className="w-3.5 h-3.5 fill-current" />
              </button>
            </div>
          </div>

          {/* Right Header Controls */}
          <div className="flex items-center space-x-3.5">
            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              title={`Switch to ${theme === 'dark' ? 'Apple Light Theme' : 'Apple Dark Theme'}`}
              className={`p-2 rounded-full border transform active:scale-95 transition-all ${
                theme === 'dark' ? 'bg-white/5 border-white/10 text-yellow-400 hover:bg-white/10' : 'bg-white border-[#e0e0e0] text-[#1d1d1f] hover:bg-black/5'
              }`}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            {/* Quick Trigger for Anomaly (Spike) status */}
            <div className={`hidden sm:flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-mono font-bold ${
              simulationAnomaly 
                ? 'bg-red-500/10 text-red-500 border border-red-500/20' 
                : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${simulationAnomaly ? 'bg-red-500 animate-ping' : 'bg-emerald-500'}`} />
              <span>{simulationAnomaly ? 'ALERT FIRED' : 'OPTIMAL'}</span>
            </div>

            {/* Live Streaming Indicator */}
            <button
              onClick={() => setIsLive(!isLive)}
              className={`text-xs px-3 py-1 rounded-full border flex items-center space-x-1.5 font-bold tracking-tight transform active:scale-95 transition-all ${
                isLive
                  ? 'bg-[#0066cc]/10 border-[#0066cc] text-[#2997ff]'
                  : 'bg-transparent border-current opacity-60 hover:opacity-100'
              }`}
            >
              <RefreshCw className={`w-3 h-3 ${isLive ? 'animate-spin' : ''}`} />
              <span>{isLive ? 'LIVE' : 'PAUSED'}</span>
            </button>
          </div>
        </header>

        {/* 3. Variables Row (DataSource, Environment, Target Node) - Direct Grafana Benchmark */}
        <section className={`px-6 py-3 border-b shrink-0 flex flex-wrap items-center gap-4 ${
          theme === 'dark' ? 'bg-[#151617] border-white/5' : 'bg-[#fafafc] border-[#e0e0e0]'
        } select-none`}>
          
          {/* Data Source Select */}
          <div className="flex items-center space-x-2">
            <span className={`text-[11px] font-bold font-mono tracking-wider uppercase ${textMuted}`}>Data Source:</span>
            <div className="relative">
              <select
                value={selectedDS}
                onChange={(e) => setSelectedDS(e.target.value)}
                className={`text-xs font-semibold py-1 pl-2.5 pr-8 rounded-md border appearance-none outline-none focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc] cursor-pointer ${
                  theme === 'dark' ? 'bg-[#222529] border-white/10 text-white' : 'bg-white border-[#e0e0e0] text-[#1d1d1f]'
                }`}
              >
                <option value="Prometheus-Seoul">Prometheus (ap-northeast-2)</option>
                <option value="InfluxDB-Metrics">InfluxDB (staging-shard)</option>
                <option value="AWSCloudWatch">CloudWatch (global-infra)</option>
                <option value="LokiLogs">Loki Logs (central-logs)</option>
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none opacity-60" />
            </div>
          </div>

          {/* Environment Select */}
          <div className="flex items-center space-x-2">
            <span className={`text-[11px] font-bold font-mono tracking-wider uppercase ${textMuted}`}>Env:</span>
            <div className="relative">
              <select
                value={selectedEnv}
                onChange={(e) => setSelectedEnv(e.target.value)}
                className={`text-xs font-semibold py-1 pl-2.5 pr-8 rounded-md border appearance-none outline-none focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc] cursor-pointer ${
                  theme === 'dark' ? 'bg-[#222529] border-white/10 text-white' : 'bg-white border-[#e0e0e0] text-[#1d1d1f]'
                }`}
              >
                <option value="production">production-vpc</option>
                <option value="staging">staging-sandbox</option>
                <option value="development">development-local</option>
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none opacity-60" />
            </div>
          </div>

          {/* Target Node Selector */}
          <div className="flex items-center space-x-2">
            <span className={`text-[11px] font-bold font-mono tracking-wider uppercase ${textMuted}`}>Node:</span>
            <div className="relative">
              <select
                value={selectedNode}
                onChange={(e) => setSelectedNode(e.target.value)}
                className={`text-xs font-semibold py-1 pl-2.5 pr-8 rounded-md border appearance-none outline-none focus:border-[#0066cc] focus:ring-1 focus:ring-[#0066cc] cursor-pointer ${
                  theme === 'dark' ? 'bg-[#222529] border-white/10 text-white' : 'bg-white border-[#e0e0e0] text-[#1d1d1f]'
                }`}
              >
                <option value="all">All Clusters (7 Nodes)</option>
                <option value="ap-east-01">ap-east-01.pod.infra</option>
                <option value="us-west-01">us-west-01.pod.infra</option>
                <option value="db-master">db-master-primary.infra</option>
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none opacity-60" />
            </div>
          </div>

          <span className="h-4 w-[1px] bg-neutral-300 dark:bg-neutral-800" />

          {/* Time range picker */}
          <div className="flex items-center space-x-1">
            <span className={`text-[11px] font-bold font-mono tracking-wider uppercase ${textMuted}`}>Range:</span>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="bg-transparent border-0 text-xs font-semibold focus:ring-0 cursor-pointer outline-none hover:text-[#0066cc] py-1 transition-colors"
            >
              <option value="15m">Last 15m</option>
              <option value="1h">Last 1h</option>
              <option value="24h">Last 24h</option>
            </select>
          </div>

          {/* Anomaly simulate */}
          <button
            onClick={toggleAnomalyState}
            className={`ml-auto px-3 py-1 rounded-full text-xs font-bold border transition-all ${
              simulationAnomaly
                ? 'bg-red-500/10 border-red-500 text-red-500 animate-pulse'
                : 'bg-transparent border-neutral-300 dark:border-neutral-800 text-inherit hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            {simulationAnomaly ? 'Clear Anomaly' : 'Trigger Anomaly'}
          </button>
        </section>

        {/* 4. Sub Navigation Bar (Integrated View Tabs selector) */}
        <div className={`px-6 py-2 border-b shrink-0 flex items-center justify-between ${
          theme === 'dark' ? 'bg-[#18191b] border-white/5' : 'bg-[#f5f5f7] border-[#e0e0e0]'
        } select-none`}>
          <div className="flex space-x-1.5">
            {[
              { id: 'overview', label: 'Cluster Panel' },
              { id: 'explore', label: 'Query Explorer' },
              { id: 'alerting', label: 'Alert Manager' },
              { id: 'connections', label: 'Data Sources' },
              { id: 'fleet', label: 'Fleet Topology' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveView(tab.id as any)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  activeView === tab.id 
                    ? 'bg-[#0066cc] text-white' 
                    : `${textMuted} hover:bg-black/5 dark:hover:bg-white/5`
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Custom Panel Add button */}
          <button
            onClick={() => setShowAddPanel(true)}
            className="bg-[#0066cc] text-white px-3 py-1.5 rounded-full text-xs font-semibold flex items-center space-x-1 hover:bg-[#0071e3] transition-colors transform active:scale-95"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Query Panel</span>
          </button>
        </div>

        {/* 5. Main stage View body (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Anomaly Alert banner */}
          <AnimatePresence>
            {simulationAnomaly && (
              <motion.div
                initial={{ opacity: 0, y: -20, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -20, height: 0 }}
                className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/30 rounded-[18px] p-5 flex items-start justify-between select-none"
              >
                <div className="flex space-x-3.5">
                  <div className="p-1.5 bg-red-100 dark:bg-red-950 rounded-full text-red-600 dark:text-red-400 mt-0.5 shrink-0 animate-pulse">
                    <ShieldAlert className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-red-800 dark:text-red-400 tracking-tight">
                      Grafana Cluster Incident Detected (Core db-master Spiking)
                    </h4>
                    <p className="text-xs text-red-700/80 dark:text-red-300/80 mt-1 leading-relaxed">
                      Severe resource limits exceeded on <strong className="font-semibold text-red-800 dark:text-red-400">db-master-primary.infra</strong>. 
                      HTTP response rate is degrading with query threshold latency exceeding 160ms. Live automated scaling is active.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleResolveAnomaly}
                  className="ml-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-full shadow-sm transform active:scale-95 transition-all shrink-0"
                >
                  Mitigate Incident
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Conditional Rendering of Primary views */}
          <AnimatePresence mode="wait">
            {activeView === 'overview' && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                className="space-y-6"
              >
                {/* 1. Metric Sparkline cards */}
                <MetricsCards
                  currentMetrics={currentMetrics}
                  history={metricsHistory}
                  simulationAnomaly={simulationAnomaly}
                  theme={theme}
                />

                {/* 2. Custom created query panels */}
                {customPanels.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {customPanels.map((panel) => (
                      <div key={panel.id} className={`${cardBg} rounded-[18px] p-5 border relative h-[250px] flex flex-col justify-between`}>
                        <div className="flex items-center justify-between mb-3 border-b border-inherit pb-2">
                          <div>
                            <h4 className="text-xs font-bold uppercase tracking-wider text-[#7a7a7a] font-mono">
                              Custom Query Panel
                            </h4>
                            <h3 className="text-sm font-semibold truncate max-w-[220px]">
                              {panel.title}
                            </h3>
                          </div>
                          <span className="text-[10px] font-mono text-[#0066cc] bg-[#0066cc]/10 px-2 py-0.5 rounded">
                            {panel.metric.toUpperCase()}
                          </span>
                        </div>

                        {/* Metric Query trace */}
                        <code className="text-[10px] text-[#7a7a7a] font-mono block bg-black/10 dark:bg-white/5 p-1 px-2 rounded truncate mb-2">
                          {panel.query}
                        </code>

                        {/* Miniature Chart simulator */}
                        <div className="flex-1 min-h-[110px] relative">
                          <AnalyticsCharts history={metricsHistory} simulationAnomaly={simulationAnomaly} theme={theme} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 3. Core Analytics Charts panel */}
                <AnalyticsCharts history={metricsHistory} simulationAnomaly={simulationAnomaly} theme={theme} />

                {/* 4. Split panel logs + fleet status */}
                <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
                  <div className="xl:col-span-3">
                    <LogViewer logs={logs} clearLogs={() => setLogs([])} theme={theme} />
                  </div>
                  <div className="xl:col-span-2">
                    <TopologyGrid
                      servers={servers}
                      simulationAnomaly={simulationAnomaly}
                      onRefresh={() => setServers(generateServerStatus())}
                      theme={theme}
                    />
                  </div>
                </div>
              </motion.div>
            )}

            {activeView === 'explore' && (
              <motion.div
                key="explore"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-6"
              >
                {/* Query deep builder stage */}
                <div className={`${cardBg} border rounded-[18px] p-6`}>
                  <div className="flex items-center justify-between mb-4 border-b border-inherit pb-3">
                    <div>
                      <h3 className="text-base font-bold tracking-tight">PromQL Query Debugger</h3>
                      <p className="text-xs text-[#7a7a7a]">Interactive telemetry trace testing</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="relative">
                      <span className="absolute left-3 top-2.5 text-xs font-mono font-bold text-[#0066cc]">Query:</span>
                      <textarea
                        defaultValue="sum(rate(node_cpu_seconds_total{mode!='idle'}[5m])) by (instance) * 100"
                        className={`w-full py-2.5 pl-16 pr-4 rounded-lg border outline-none font-mono text-xs ${
                          theme === 'dark' ? 'bg-[#151617] border-white/10 text-teal-400' : 'bg-[#fafafc] border-[#e0e0e0] text-[#0066cc]'
                        }`}
                        rows={3}
                      />
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className={textMuted}>Parsed variables: Node="{selectedNode}", Env="{selectedEnv}"</span>
                      <button className="bg-[#0066cc] text-white px-4 py-2 rounded-full font-semibold flex items-center space-x-1">
                        <Activity className="w-4 h-4" />
                        <span>Execute PromQL Trace</span>
                      </button>
                    </div>
                  </div>
                </div>

                <AnalyticsCharts history={metricsHistory} simulationAnomaly={simulationAnomaly} theme={theme} />
              </motion.div>
            )}

            {activeView === 'alerting' && (
              <motion.div
                key="alerting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <AlertingRules 
                  simulationAnomaly={simulationAnomaly} 
                  toggleAnomaly={toggleAnomalyState} 
                  theme={theme}
                />
              </motion.div>
            )}

            {activeView === 'connections' && (
              <motion.div
                key="connections"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Connections theme={theme} />
              </motion.div>
            )}

            {activeView === 'fleet' && (
              <motion.div
                key="fleet"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <TopologyGrid
                  servers={servers}
                  simulationAnomaly={simulationAnomaly}
                  onRefresh={() => setServers(generateServerStatus())}
                  theme={theme}
                />
              </motion.div>
            )}

            {activeView === 'variables' && (
              <motion.div
                key="variables"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={`${cardBg} rounded-[18px] border p-6 max-w-2xl mx-auto`}
              >
                <h3 className="text-base font-bold mb-2">Variables Configurator</h3>
                <p className="text-xs text-[#7a7a7a] mb-4">
                  Define user variables to interpolate dynamically across panel queries.
                </p>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex justify-between p-3 border-b border-inherit">
                    <span className="font-semibold text-[#0066cc]">$datasource</span>
                    <span>Prometheus (Global Pool)</span>
                  </div>
                  <div className="flex justify-between p-3 border-b border-inherit">
                    <span className="font-semibold text-[#0066cc]">$env</span>
                    <span>production, staging, development</span>
                  </div>
                  <div className="flex justify-between p-3 border-b border-inherit">
                    <span className="font-semibold text-[#0066cc]">$node</span>
                    <span>All cluster nodes (Auto-routing active)</span>
                  </div>
                </div>
              </motion.div>
            )}

            {activeView === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className={`${cardBg} rounded-[18px] border p-6 max-w-2xl mx-auto`}
              >
                <h3 className="text-base font-bold mb-2">System Preferences</h3>
                <p className="text-xs text-[#7a7a7a] mb-4">
                  Global parameters managing tracing density and metrics polling intervals.
                </p>

                <div className="space-y-4 text-xs">
                  <div className="flex justify-between items-center p-3 border-b border-inherit">
                    <div>
                      <p className="font-semibold">Metrics Polling rate</p>
                      <p className="text-[10px] text-[#7a7a7a]">Telemetry sync interval</p>
                    </div>
                    <span className="font-mono text-[#0066cc] font-bold">15000ms</span>
                  </div>
                  <div className="flex justify-between items-center p-3 border-b border-inherit">
                    <div>
                      <p className="font-semibold">Loki log stream length</p>
                      <p className="text-[10px] text-[#7a7a7a]">Log stream slide window size</p>
                    </div>
                    <span className="font-mono text-[#0066cc] font-bold">150 lines</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* 6. Dynamic Floating-Sticky-Bar (Incident Mitigation Trigger, bottom center) */}
      <AnimatePresence>
        {simulationAnomaly && (
          <motion.div
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 100 }}
            className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-[calc(100%-2rem)] max-w-lg bg-[#18191b]/95 backdrop-blur-md border border-red-500/30 rounded-full px-6 py-3 shadow-2xl flex items-center justify-between z-50 select-none"
          >
            <div className="flex items-center space-x-3 overflow-hidden">
              <span className="flex h-2 w-2 rounded-full bg-red-500 animate-ping shrink-0" />
              <span className="text-xs font-mono font-semibold text-white truncate">
                Active incident on node ap-east-01
              </span>
            </div>
            <button
              onClick={handleResolveAnomaly}
              className="bg-[#0066cc] hover:bg-[#0071e3] text-white px-4 py-1.5 rounded-full text-xs font-semibold transform active:scale-95 transition-all shrink-0"
            >
              Mitigate Cluster Spike
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Add Custom Query Panel Dialog / Pop-up */}
      <AnimatePresence>
        {showAddPanel && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className={`border rounded-[18px] p-6 max-w-md w-full relative ${cardBg}`}
            >
              <h3 className="text-base font-bold mb-1">Add Custom Grafana Panel</h3>
              <p className="text-xs text-[#7a7a7a] mb-4">
                Define the query trace logic and metric targeting
              </p>

              <form onSubmit={handleCreatePanel} className="space-y-4">
                {/* Title */}
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#7a7a7a] font-mono block">PANEL TITLE</label>
                  <input
                    type="text"
                    required
                    value={newPanelTitle}
                    onChange={(e) => setNewPanelTitle(e.target.value)}
                    placeholder="e.g. Ingress Controller Bottleneck"
                    className={`w-full py-2 px-3 rounded-md border text-xs outline-none ${
                      theme === 'dark' ? 'bg-[#222529] border-white/10 text-white' : 'bg-white border-[#e0e0e0]'
                    }`}
                  />
                </div>

                {/* Target Metric Metric Preset */}
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#7a7a7a] font-mono block">TARGET SYSTEM METRIC</label>
                  <select
                    value={newPanelMetric}
                    onChange={(e) => setNewPanelMetric(e.target.value as any)}
                    className={`w-full py-2 px-3 rounded-md border text-xs outline-none cursor-pointer ${
                      theme === 'dark' ? 'bg-[#222529] border-white/10 text-white' : 'bg-white border-[#e0e0e0]'
                    }`}
                  >
                    <option value="cpu">CPU Usage (%)</option>
                    <option value="memory">Memory Buffer (%)</option>
                    <option value="requestRate">HTTP Traffic Ingestion (req/s)</option>
                    <option value="responseTime">Gateway P95 Latency (ms)</option>
                  </select>
                </div>

                {/* Query input */}
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-[#7a7a7a] font-mono block">PROMQL EXECUTION QUERY</label>
                  <textarea
                    value={newPanelQuery}
                    onChange={(e) => setNewPanelQuery(e.target.value)}
                    placeholder='avg(rate(system_metrics_total{tier="gateway"}[5m]))'
                    className={`w-full py-2 px-3 rounded-md border text-xs font-mono outline-none ${
                      theme === 'dark' ? 'bg-[#222529] border-white/10 text-teal-400' : 'bg-white border-[#e0e0e0] text-[#0066cc]'
                    }`}
                    rows={2}
                  />
                </div>

                {/* Action CTA */}
                <div className="flex space-x-2 justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddPanel(false)}
                    className="px-4 py-2 rounded-full text-xs font-semibold hover:bg-black/5 dark:hover:bg-white/5"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-[#0066cc] text-white px-4 py-2 rounded-full text-xs font-semibold hover:bg-[#0071e3]"
                  >
                    Provision Panel
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
