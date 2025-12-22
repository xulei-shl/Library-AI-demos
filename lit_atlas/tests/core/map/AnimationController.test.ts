/**
 * AnimationController 单元测试
 */

import { AnimationController, AnimationState } from '@/core/map/animation/AnimationController';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';

describe('AnimationController', () => {
  let controller: AnimationController;

  beforeEach(() => {
    controller = new AnimationController({
      growthDuration: 1000,
      rippleDuration: 500,
      flowSpeed: 1
    });
  });

  afterEach(() => {
    controller.destroy();
  });

  describe('Feature Registration', () => {
    it('should register feature with animation metadata', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 1000);
      const meta = controller.getFeatureMeta(feature);

      expect(meta).toBeDefined();
      expect(meta?.startTime).toBe(0);
      expect(meta?.duration).toBe(1000);
      expect(meta?.state).toBe(AnimationState.HIDDEN);
    });

    it('should return undefined for unregistered feature', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      const meta = controller.getFeatureMeta(feature);
      expect(meta).toBeUndefined();
    });
  });

  describe('Animation State Calculation', () => {
    it('should return HIDDEN before start time', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 1000, 2000);
      controller.setTime(500);

      const state = controller.calculateFeatureState(feature);
      expect(state).toBe(AnimationState.HIDDEN);
    });

    it('should return GROWING during growth phase', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 2000);
      controller.setTime(500); // 500ms into 1000ms growth

      const state = controller.calculateFeatureState(feature);
      expect(state).toBe(AnimationState.GROWING);
    });

    it('should return RIPPLING during ripple phase', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 2000);
      controller.setTime(1200); // After growth, during ripple

      const state = controller.calculateFeatureState(feature);
      expect(state).toBe(AnimationState.RIPPLING);
    });

    it('should return ACTIVE after all animations complete', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 2000);
      controller.setTime(2000); // After growth + ripple

      const state = controller.calculateFeatureState(feature);
      expect(state).toBe(AnimationState.ACTIVE);
    });
  });

  describe('Progress Calculation', () => {
    it('should calculate progress correctly during GROWING', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 2000);
      controller.setTime(500); // 50% through growth

      const progress = controller.calculateProgress(feature);
      expect(progress).toBeCloseTo(0.5, 1);
    });

    it('should return 0 for HIDDEN state', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 1000, 2000);
      controller.setTime(0);

      const progress = controller.calculateProgress(feature);
      expect(progress).toBe(0);
    });

    it('should return 1 for ACTIVE state', () => {
      const feature = new Feature({
        geometry: new Point([0, 0])
      });

      controller.registerFeature(feature, 0, 2000);
      controller.setTime(2000);

      const progress = controller.calculateProgress(feature);
      expect(progress).toBe(1);
    });
  });

  describe('Time Control', () => {
    it('should set and get current time', () => {
      controller.setTime(1000);
      expect(controller.getTime()).toBe(1000);
    });

    it('should trigger update callbacks on time change', () => {
      const callback = jest.fn();
      controller.onUpdate(callback);

      controller.setTime(500);
      expect(callback).toHaveBeenCalled();
    });
  });

  describe('Playback Control', () => {
    it('should start and stop playback', () => {
      controller.play();
      // Note: Testing actual animation loop requires mocking requestAnimationFrame
      controller.pause();
      // Should not throw
    });

    it('should allow unsubscribing from updates', () => {
      const callback = jest.fn();
      const unsubscribe = controller.onUpdate(callback);

      controller.setTime(100);
      expect(callback).toHaveBeenCalledTimes(1);

      unsubscribe();
      controller.setTime(200);
      expect(callback).toHaveBeenCalledTimes(1); // Not called again
    });
  });
});
