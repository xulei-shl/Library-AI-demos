/**
 * 个人星图持久化管理
 * 参考：@docs/design/personal_constellation_module_20251215.md
 */

import type { ConstellationData, UserMark } from './types';

const STORAGE_KEY = 'lit_atlas_constellation';
const CURRENT_VERSION = 1;
const MAX_STORAGE_SIZE = 5 * 1024 * 1024; // 5MB

/**
 * 检查 localStorage 可用性
 */
function isStorageAvailable(): boolean {
  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

/**
 * 估算数据大小
 */
function estimateSize(data: ConstellationData): number {
  return new Blob([JSON.stringify(data)]).size;
}

/**
 * 加载用户标记
 */
export function loadMarks(): UserMark[] {
  if (!isStorageAvailable()) {
    console.warn('[Constellation] localStorage not available');
    return [];
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const data: ConstellationData = JSON.parse(raw);
    
    // 版本迁移
    if (data.version < CURRENT_VERSION) {
      return migrateData(data);
    }

    return data.marks;
  } catch (error) {
    console.error('[Constellation] Failed to load marks:', error);
    return [];
  }
}

/**
 * 保存用户标记
 */
export function saveMarks(marks: UserMark[]): boolean {
  if (!isStorageAvailable()) {
    console.warn('[Constellation] localStorage not available');
    return false;
  }

  const data: ConstellationData = {
    version: CURRENT_VERSION,
    marks,
    lastUpdated: Date.now(),
  };

  // 检查容量
  const size = estimateSize(data);
  if (size > MAX_STORAGE_SIZE) {
    console.error('[Constellation] Data exceeds storage limit');
    return false;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    return true;
  } catch (error) {
    console.error('[Constellation] Failed to save marks:', error);
    return false;
  }
}

/**
 * 导出为 JSON
 */
export function exportToJSON(marks: UserMark[]): string {
  const data: ConstellationData = {
    version: CURRENT_VERSION,
    marks,
    lastUpdated: Date.now(),
  };
  return JSON.stringify(data, null, 2);
}

/**
 * 从 JSON 导入
 */
export function importFromJSON(json: string): UserMark[] | null {
  try {
    const data: ConstellationData = JSON.parse(json);
    if (data.version < CURRENT_VERSION) {
      return migrateData(data);
    }
    return data.marks;
  } catch (error) {
    console.error('[Constellation] Failed to import JSON:', error);
    return null;
  }
}

/**
 * 清空所有标记
 */
export function clearMarks(): void {
  if (isStorageAvailable()) {
    localStorage.removeItem(STORAGE_KEY);
  }
}

/**
 * 数据迁移
 */
function migrateData(oldData: ConstellationData): UserMark[] {
  // 当前只有 v1，未来版本在此处理迁移逻辑
  return oldData.marks;
}
