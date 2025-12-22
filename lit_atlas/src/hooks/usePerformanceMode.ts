/**
 * 性能模式 Hook
 * 根据设备能力自动调整性能配置
 */

'use client';

import { useEffect, useState } from 'react';
import { getPerformanceConfig, type PerformanceConfig } from '@/utils/performanceOptimizer';

/**
 * 使用性能模式
 */
export function usePerformanceMode(): PerformanceConfig {
  const [config, setConfig] = useState<PerformanceConfig>(() => getPerformanceConfig());

  useEffect(() => {
    // 监听 prefers-reduced-motion 变化
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    const handleChange = () => {
      setConfig(getPerformanceConfig());
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return config;
}
