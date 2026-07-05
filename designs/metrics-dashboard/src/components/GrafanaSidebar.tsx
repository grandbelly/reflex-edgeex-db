/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  Menu, 
  LayoutDashboard, 
  Compass, 
  Bell, 
  Sliders, 
  Settings, 
  HelpCircle, 
  Search, 
  ChevronRight, 
  ChevronLeft,
  Flame,
  Layers,
  Database,
  Grid
} from 'lucide-react';

interface GrafanaSidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  activeView: string;
  setActiveView: (view: any) => void;
  theme: 'light' | 'dark';
}

export default function GrafanaSidebar({ 
  isOpen, 
  setIsOpen, 
  activeView, 
  setActiveView,
  theme 
}: GrafanaSidebarProps) {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const menuItems = [
    { id: 'overview', label: 'Dashboards', icon: LayoutDashboard, badge: null },
    { id: 'explore', label: 'Explore (Queries)', icon: Compass, badge: 'New' },
    { id: 'alerting', label: 'Alerting rules', icon: Bell, badge: '2' },
    { id: 'connections', label: 'Connections', icon: Database, badge: null },
    { id: 'fleet', label: 'Node Topology', icon: Grid, badge: null },
    { id: 'variables', label: 'Variables', icon: Sliders, badge: null },
    { id: 'settings', label: 'Administration', icon: Settings, badge: null },
  ];

  const sidebarBg = theme === 'dark' ? 'bg-[#18191b] border-white/5' : 'bg-[#fafafc] border-[#e0e0e0]';
  const textColor = theme === 'dark' ? 'text-white' : 'text-[#1d1d1f]';
  const textMuted = theme === 'dark' ? 'text-white/60' : 'text-[#7a7a7a]';
  const hoverBg = theme === 'dark' ? 'hover:bg-white/5' : 'hover:bg-black/5';

  return (
    <aside
      id="grafana-sidebar"
      className={`apple-transition shrink-0 border-r h-full flex flex-col justify-between z-40 relative select-none ${sidebarBg} ${
        isOpen ? 'w-64' : 'w-16'
      }`}
    >
      {/* Top Brand Logo / Header */}
      <div>
        <div className="h-14 flex items-center justify-between px-4 border-b border-inherit">
          <div className="flex items-center space-x-3 overflow-hidden">
            {/* Grafana-like gradient logo but styled beautifully */}
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#ff4a00] via-[#ff7c00] to-[#ffb800] p-1.5 flex items-center justify-center shadow-md shrink-0">
              <Flame className="w-5 h-5 text-white" />
            </div>
            {isOpen && (
              <div className="flex flex-col">
                <span className={`text-[13px] font-bold tracking-tight ${textColor}`}>Grafana</span>
                <span className="text-[10px] font-mono text-[#0066cc] font-semibold uppercase tracking-wider">
                  Apple Mode
                </span>
              </div>
            )}
          </div>
          
          {/* Toggle Button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className={`p-1.5 rounded-full ${hoverBg} ${textMuted} transition-colors hidden md:block`}
          >
            {isOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        {/* Quick Search */}
        {isOpen && (
          <div className="p-3">
            <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs border ${
              theme === 'dark' ? 'bg-white/5 border-white/10 text-white/40' : 'bg-[#f5f5f7] border-[#e0e0e0] text-[#7a7a7a]'
            }`}>
              <Search className="w-3.5 h-3.5" />
              <input 
                type="text" 
                placeholder="Find dashboard..." 
                className="bg-transparent border-0 outline-none w-full text-xs py-0 focus:ring-0 text-inherit placeholder-current"
                disabled
              />
              <span className="font-mono text-[9px] opacity-60">⌘K</span>
            </div>
          </div>
        )}

        {/* Sidebar Menu Items */}
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                onMouseEnter={() => setHoveredItem(item.id)}
                onMouseLeave={() => setHoveredItem(null)}
                className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-medium apple-transition relative group ${
                  isActive 
                    ? theme === 'dark' 
                      ? 'bg-white/10 text-white' 
                      : 'bg-[#0066cc]/10 text-[#0066cc]'
                    : `${textMuted} ${hoverBg}`
                }`}
              >
                <div className="flex items-center space-x-3.5 overflow-hidden">
                  <Icon className={`w-4.5 h-4.5 shrink-0 ${
                    isActive ? (theme === 'dark' ? 'text-white' : 'text-[#0066cc]') : ''
                  }`} />
                  {isOpen && (
                    <span className={`tracking-tight ${isActive ? 'font-semibold' : ''}`}>
                      {item.label}
                    </span>
                  )}
                </div>

                {/* Badges/Indicators */}
                {isOpen && item.badge && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold font-mono uppercase ${
                    item.id === 'alerting' 
                      ? 'bg-red-500 text-white animate-pulse' 
                      : theme === 'dark' ? 'bg-white/10 text-white/80' : 'bg-black/10 text-[#1d1d1f]'
                  }`}>
                    {item.badge}
                  </span>
                )}

                {/* Tooltip for collapsed mode */}
                {!isOpen && hoveredItem === item.id && (
                  <div className={`absolute left-16 px-3 py-1.5 rounded-md text-[11px] font-sans font-semibold shadow-xl border z-50 whitespace-nowrap ${
                    theme === 'dark' 
                      ? 'bg-[#1d1d1f] border-white/10 text-white' 
                      : 'bg-white border-[#e0e0e0] text-[#1d1d1f]'
                  }`}>
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Footer User Info */}
      <div className="p-3 border-t border-inherit">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="w-8 h-8 rounded-full bg-[#0066cc] flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-inner">
            U
          </div>
          {isOpen && (
            <div className="flex flex-col overflow-hidden">
              <span className={`text-xs font-semibold truncate ${textColor}`}>grandbelly@knou.ac.kr</span>
              <span className="text-[10px] font-mono opacity-50 truncate">Viewer Role</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
