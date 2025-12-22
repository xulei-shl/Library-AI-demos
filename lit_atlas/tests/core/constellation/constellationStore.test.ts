/**
 * 个人星图 Store 单元测试
 */

import { useConstellationStore } from '@/core/constellation/constellationStore';
import type { UserMark } from '@/core/constellation/types';

// Mock persistence
jest.mock('@/core/constellation/persistence', () => ({
  loadMarks: jest.fn(() => []),
  saveMarks: jest.fn(() => true),
}));

describe('ConstellationStore', () => {
  beforeEach(() => {
    // 重置 store
    useConstellationStore.setState({
      marks: [],
      visible: true,
      enabled: true,
    });
  });

  describe('addMark', () => {
    it('should add new mark', () => {
      const { addMark, marks } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'read', 'Great city!');
      
      const state = useConstellationStore.getState();
      expect(state.marks).toHaveLength(1);
      expect(state.marks[0]).toMatchObject({
        authorId: 'murakami',
        cityId: 'tokyo',
        status: 'read',
        note: 'Great city!',
      });
    });

    it('should update existing mark', () => {
      const { addMark } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'wish');
      addMark('murakami', 'tokyo', 'read', 'Updated!');
      
      const state = useConstellationStore.getState();
      expect(state.marks).toHaveLength(1);
      expect(state.marks[0].status).toBe('read');
      expect(state.marks[0].note).toBe('Updated!');
    });
  });

  describe('removeMark', () => {
    it('should remove mark', () => {
      const { addMark, removeMark } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'read');
      addMark('murakami', 'kyoto', 'wish');
      
      removeMark('murakami', 'tokyo');
      
      const state = useConstellationStore.getState();
      expect(state.marks).toHaveLength(1);
      expect(state.marks[0].cityId).toBe('kyoto');
    });
  });

  describe('getMark', () => {
    it('should get mark by authorId and cityId', () => {
      const { addMark, getMark } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'read');
      
      const mark = getMark('murakami', 'tokyo');
      expect(mark).toBeDefined();
      expect(mark?.status).toBe('read');
    });

    it('should return undefined for non-existent mark', () => {
      const { getMark } = useConstellationStore.getState();
      
      const mark = getMark('murakami', 'tokyo');
      expect(mark).toBeUndefined();
    });
  });

  describe('getMarksByAuthor', () => {
    it('should get all marks for author', () => {
      const { addMark, getMarksByAuthor } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'read');
      addMark('murakami', 'kyoto', 'wish');
      addMark('marquez', 'bogota', 'read');
      
      const marks = getMarksByAuthor('murakami');
      expect(marks).toHaveLength(2);
      expect(marks.every(m => m.authorId === 'murakami')).toBe(true);
    });
  });

  describe('toggleVisibility', () => {
    it('should toggle visibility', () => {
      const { toggleVisibility } = useConstellationStore.getState();
      
      expect(useConstellationStore.getState().visible).toBe(true);
      
      toggleVisibility();
      expect(useConstellationStore.getState().visible).toBe(false);
      
      toggleVisibility();
      expect(useConstellationStore.getState().visible).toBe(true);
    });
  });

  describe('clearAll', () => {
    it('should clear all marks', () => {
      const { addMark, clearAll } = useConstellationStore.getState();
      
      addMark('murakami', 'tokyo', 'read');
      addMark('marquez', 'bogota', 'wish');
      
      clearAll();
      
      const state = useConstellationStore.getState();
      expect(state.marks).toHaveLength(0);
    });
  });
});
