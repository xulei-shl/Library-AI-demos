/**
 * PlaybackControl 组件测试
 * 参考：@docs/design/playback_control_module_20251215.md
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PlaybackControl } from '@/core/playback/PlaybackControl';
import { NarrativeScheduler } from '@/core/scheduler/narrativeScheduler';
import type { Route } from '@/core/data/normalizers';

describe('PlaybackControl', () => {
  let scheduler: NarrativeScheduler;
  const mockRoutes: Route[] = [
    {
      id: 'route1',
      start_location: {
        name: 'city1',
        coordinates: { lat: 0, lng: 0 },
      },
      end_location: {
        name: 'city2',
        coordinates: { lat: 1, lng: 1 },
      },
      year: 1920,
      collection_info: {
        has_collection: true,
        collection_meta: {
          title: 'Test Work',
          date: '1920',
          location: 'city1',
        },
      },
    },
  ];

  beforeEach(() => {
    scheduler = new NarrativeScheduler();
    const mockAuthor = {
      id: 'test',
      name: 'Test',
      name_zh: '测试',
      theme_color: '#2c3e50',
      routes: mockRoutes,
    };
    scheduler.load(mockAuthor, mockRoutes);
  });

  afterEach(() => {
    scheduler.dispose();
  });

  it('应该渲染播放控制组件', () => {
    render(<PlaybackControl scheduler={scheduler} />);
    expect(screen.getByRole('region', { name: '播放控制' })).toBeInTheDocument();
  });

  it('应该显示播放/暂停按钮', () => {
    render(<PlaybackControl scheduler={scheduler} />);
    const playButton = screen.getByLabelText('播放');
    expect(playButton).toBeInTheDocument();
  });

  it('点击播放按钮应该开始播放', async () => {
    render(<PlaybackControl scheduler={scheduler} />);
    const playButton = screen.getByLabelText('播放');
    
    fireEvent.click(playButton);
    
    await waitFor(() => {
      expect(screen.getByLabelText('暂停')).toBeInTheDocument();
    });
  });

  it('应该显示进度条', () => {
    render(<PlaybackControl scheduler={scheduler} />);
    const slider = screen.getByRole('slider', { name: '播放进度' });
    expect(slider).toBeInTheDocument();
  });

  it('应该显示速度菜单', () => {
    render(<PlaybackControl scheduler={scheduler} />);
    const speedButton = screen.getByLabelText(/播放速度/);
    expect(speedButton).toBeInTheDocument();
  });

  it('应该显示时间', () => {
    render(<PlaybackControl scheduler={scheduler} />);
    expect(screen.getByText('0:00')).toBeInTheDocument();
  });

  it('应该支持快捷键播放/暂停', async () => {
    render(<PlaybackControl scheduler={scheduler} enableHotkeys={true} />);
    
    fireEvent.keyDown(window, { key: ' ' });
    
    await waitFor(() => {
      expect(screen.getByLabelText('暂停')).toBeInTheDocument();
    });
  });

  it('禁用快捷键时不应响应按键', () => {
    render(<PlaybackControl scheduler={scheduler} enableHotkeys={false} />);
    
    fireEvent.keyDown(window, { key: ' ' });
    
    expect(screen.getByLabelText('播放')).toBeInTheDocument();
  });
});
