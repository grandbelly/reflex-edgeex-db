/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Terminal, Search, Trash2, SlidersHorizontal, AlertTriangle, CheckCircle, Info, ChevronRight, ChevronDown } from 'lucide-react';
import { LogEntry, LogLevel } from '../types';

interface LogViewerProps {
  logs: LogEntry[];
  clearLogs: () => void;
  theme?: 'light' | 'dark';
}

export default function LogViewer({ logs, clearLogs, theme = 'dark' }: LogViewerProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [levelFilter, setLevelFilter] = useState<LogLevel | 'all'>('all');
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const isDark = theme === 'dark';
  const containerBg = isDark ? 'bg-[#18191b] border-white/5 shadow-2xl text-white' : 'bg-white border-[#e0e0e0] shadow-sm text-[#1d1d1f]';
  const textTitleColor = isDark ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = isDark ? 'text-[#cccccc]/70' : 'text-[#7a7a7a]';
  const inputBg = isDark ? 'bg-white/5 border-white/10 text-white placeholder-white/20 focus:border-[#2997ff] focus:ring-[#2997ff]' : 'bg-[#f5f5f7] border-[#e0e0e0] text-[#1d1d1f] placeholder-black/30 focus:border-[#0066cc] focus:ring-[#0066cc]';
  const inputIconColor = isDark ? 'text-white/30' : 'text-black/30';
  const consoleBg = isDark ? 'bg-[#000000]/45 border-white/5 text-white/80' : 'bg-[#fafafc] border-[#e0e0e0] text-[#1d1d1f]/80';
  const borderDivider = isDark ? 'border-white/5' : 'border-[#e0e0e0]';
  const logBorderDivider = isDark ? 'border-white/5' : 'border-black/5';
  const hoverBg = isDark ? 'hover:bg-white/5' : 'hover:bg-black/5';
  const detailBg = isDark ? 'bg-white/5 border-white/10 text-[#cccccc]' : 'bg-[#f5f5f7] border-[#e0e0e0] text-[#1d1d1f]/80';
  const inlineCodeBg = isDark ? 'bg-black/30 border-white/5 text-white' : 'bg-white border-black/5 text-[#1d1d1f]';
  const activeBtnBg = isDark ? 'bg-white/10 text-white' : 'bg-black/10 text-[#1d1d1f]';
  const inactiveBtnText = isDark ? 'text-white/40 hover:text-white/80' : 'text-black/40 hover:text-black/80';
  const tagColor = isDark ? 'text-[#2997ff]' : 'text-[#0066cc]';

  // Auto-scroll logic
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.service.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesLevel = levelFilter === 'all' || log.level === levelFilter;
    return matchesSearch && matchesLevel;
  });

  const getLevelBadge = (level: LogLevel) => {
    switch (level) {
      case 'error':
        return (
          <span className="inline-flex items-center space-x-1 bg-red-500/10 text-red-500 px-2 py-0.5 rounded-sm text-[10px] font-bold">
            <AlertTriangle className="h-3 w-3" />
            <span>ERR</span>
          </span>
        );
      case 'warn':
        return (
          <span className="inline-flex items-center space-x-1 bg-amber-500/10 text-amber-500 px-2 py-0.5 rounded-sm text-[10px] font-bold">
            <AlertTriangle className="h-3 w-3" />
            <span>WRN</span>
          </span>
        );
      case 'success':
        return (
          <span className="inline-flex items-center space-x-1 bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded-sm text-[10px] font-bold">
            <CheckCircle className="h-3 w-3" />
            <span>OK</span>
          </span>
        );
      case 'info':
      default:
        return (
          <span className={`inline-flex items-center space-x-1 ${isDark ? 'bg-blue-500/10 text-[#2997ff]' : 'bg-[#0066cc]/10 text-[#0066cc]'} px-2 py-0.5 rounded-sm text-[10px] font-bold`}>
            <Info className="h-3 w-3" />
            <span>INF</span>
          </span>
        );
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className={`rounded-[18px] p-6 flex flex-col h-[520px] border relative overflow-hidden apple-transition ${containerBg}`}
    >
      {/* Header of Log Viewer */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 select-none">
        <div className="flex items-center space-x-2.5">
          <Terminal className={`h-5 w-5 ${tagColor}`} />
          <div>
            <h3 className={`text-base font-semibold tracking-tight ${textTitleColor}`}>System Logs Stream</h3>
            <p className={`text-[11px] font-mono ${textMuted}`}>Consolidated telemetry streaming</p>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Level Filter Tags */}
          <div className={`flex p-0.5 rounded-sm text-xs font-mono ${isDark ? 'bg-white/5' : 'bg-black/5'}`}>
            {(['all', 'info', 'success', 'warn', 'error'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setLevelFilter(lvl)}
                className={`px-2 py-0.5 rounded-xs uppercase text-[10px] font-semibold transition-all ${
                  levelFilter === lvl ? activeBtnBg : inactiveBtnText
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>

          {/* Clean Trigger */}
          <button
            onClick={clearLogs}
            title="Purge logs buffer"
            className={`p-1.5 rounded transition-all flex items-center ${
              isDark ? 'bg-white/5 hover:bg-red-500/20 text-white/60 hover:text-red-400' : 'bg-black/5 hover:bg-red-500/10 text-black/60 hover:text-red-600'
            }`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Refined Search Input (Apple style: Search-input search-input-pill) */}
      <div className="relative mb-3 flex items-center">
        <Search className={`absolute left-3.5 h-4 w-4 ${inputIconColor}`} />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter logs by keyword or microservice..."
          className={`w-full border rounded-full py-2.5 pl-10 pr-4 text-xs font-mono outline-none apple-transition ${inputBg}`}
        />
        {filteredLogs.length > 0 && (
          <span className={`absolute right-4 text-[9px] font-mono ${isDark ? 'text-white/30' : 'text-black/40'}`}>
            {filteredLogs.length} entries
          </span>
        )}
      </div>

      {/* Logs Console Container */}
      <div
        ref={scrollContainerRef}
        className={`flex-1 overflow-y-auto font-mono text-xs space-y-1.5 pr-2 mb-3 p-4 rounded-lg border scrollbar-thin ${consoleBg}`}
      >
        <AnimatePresence initial={false}>
          {filteredLogs.length === 0 ? (
            <div className={`h-full flex flex-col items-center justify-center space-y-2 py-10 ${isDark ? 'text-white/20' : 'text-black/20'}`}>
              <Terminal className="h-8 w-8 stroke-[1]" />
              <p className="text-xs">No matching log entries found.</p>
            </div>
          ) : (
            filteredLogs.map((log) => {
              const isSelected = selectedLogId === log.id;
              return (
                <div key={log.id} className={`flex flex-col border-b pb-1 ${logBorderDivider}`}>
                  <div
                    onClick={() => setSelectedLogId(isSelected ? null : log.id)}
                    className={`flex items-start justify-between cursor-pointer py-1.5 px-2 rounded-sm transition-all ${hoverBg}`}
                  >
                    <div className="flex items-start space-x-2.5 overflow-hidden">
                      {/* Chevron Toggle */}
                      {isSelected ? (
                        <ChevronDown className={`h-3.5 w-3.5 mt-0.5 ${isDark ? 'text-white/30' : 'text-black/35'}`} />
                      ) : (
                        <ChevronRight className={`h-3.5 w-3.5 mt-0.5 ${isDark ? 'text-white/30' : 'text-black/35'}`} />
                      )}

                      {/* Log Timestamp */}
                      <span className={`font-mono text-[10px] select-none mt-0.5 ${isDark ? 'text-white/40' : 'text-black/40'}`}>
                        {new Date(log.timestamp).toLocaleTimeString('ko-KR', { hour12: false })}
                      </span>

                      {/* Level */}
                      <span className="shrink-0">{getLevelBadge(log.level)}</span>

                      {/* Service tag */}
                      <span className={`text-[10px] font-bold uppercase tracking-wider shrink-0 mt-0.5 ${tagColor}`}>
                        [{log.service}]
                      </span>

                      {/* Message */}
                      <span className={`truncate font-sans tracking-wide ${isDark ? 'text-white/90' : 'text-black/90'}`}>
                        {log.message}
                      </span>
                    </div>

                    {/* Duration helper if present */}
                    {log.duration !== undefined && (
                      <span className={`text-[10px] font-mono px-1 rounded-sm ${
                        log.duration > 200 
                          ? 'text-red-500 font-bold' 
                          : isDark ? 'text-white/40' : 'text-black/40'
                      }`}>
                        {log.duration}ms
                      </span>
                    )}
                  </div>

                  {/* Expanded Detailed Node JSON info block */}
                  {isSelected && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className={`border rounded-sm p-3 mt-1.5 mx-8 text-[11px] space-y-2 ${detailBg}`}
                    >
                      <div className={`grid grid-cols-2 gap-2 border-b pb-2 mb-2 font-mono ${logBorderDivider}`}>
                        <div>
                          <span className={isDark ? 'text-white/30' : 'text-black/40'}>Trace Identifier:</span>{' '}
                          <span className={tagColor}>{log.id}</span>
                        </div>
                        <div>
                          <span className={isDark ? 'text-white/30' : 'text-black/40'}>Target Service:</span>{' '}
                          <span>{log.service}.production.node</span>
                        </div>
                      </div>
                      <div className="font-sans text-xs">
                        <span className={`font-mono text-[11px] ${isDark ? 'text-white/30' : 'text-black/40'}`}>Full Payload Message:</span>
                        <p className={`mt-1 p-2 rounded border ${inlineCodeBg}`}>
                          {log.message}
                        </p>
                      </div>
                      <div className={`flex items-center justify-between text-[10px] font-mono pt-1 ${isDark ? 'text-white/35' : 'text-black/40'}`}>
                        <span>ISO Date: {log.timestamp}</span>
                        <span>Severity Class: {log.level.toUpperCase()}</span>
                      </div>
                    </motion.div>
                  )}
                </div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Footer log monitor stats */}
      <div className={`flex items-center justify-between text-[10px] font-mono select-none ${isDark ? 'text-[#cccccc]/50' : 'text-[#7a7a7a]'}`}>
        <div className="flex items-center space-x-4">
          <span>Active Ingestion: Live WebSocket</span>
          <div className="flex items-center space-x-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Trace Engine Active</span>
          </div>
        </div>

        {/* Autoscroll toggle lock */}
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border transition-all ${
            autoScroll
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : isDark ? 'bg-white/5 border-white/10 text-white/40' : 'bg-black/5 border-[#e0e0e0] text-black/40'
          }`}
        >
          {autoScroll ? '● AUTO SCROLL ON' : '○ SCROLL LOCK'}
        </button>
      </div>
    </motion.div>
  );
}
