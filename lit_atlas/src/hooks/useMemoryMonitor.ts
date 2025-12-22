/**
 * 内存监控 Hook
 */

'use client';

import { useEffect, useState } from 'react';
import { MemoryMonitor } from '@/utils/memoryMonitor';

interface MemoryStats {
  current: string;
  average: string;
  peak: string;
  trend: 'stable' | 'increasing' | 'decreasing';
}

/**
 * 使用内存监控
 */
export function useMemoryMonitor(enabled = false, intervalMs = 1000): MemoryStats | null {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [monitor] = useState(() => new MemoryMonitor());

  useEffect(() => {
    if (!enabled) return;

    monitor.start(intervalMs);

    const updateInterval = setInterval(() => {
      const currentStats = monitor.getStats();
      if (currentStats) {
        setStats(currentStats);
      }
    }, intervalMs);

    return () => {
      clearInterval(updateInterval);
      monitor.stop();
    };
  }, [enabled, intervalMs, monitor]);

  return stats;
}
