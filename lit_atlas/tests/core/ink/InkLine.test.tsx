/**
 * InkLine组件测试
 */

import React from 'react';
import { render } from '@testing-library/react';
import { InkLine } from '../../../src/core/ink/InkLine';

describe('InkLine', () => {
  const mockProps = {
    routeId: 'test-route',
    coordinates: [
      [116.4, 39.9],
      [121.5, 31.2],
    ] as [number, number][],
    progress: 0,
    color: '#2c3e50',
    duration: 2000,
  };

  it('应该正确渲染', () => {
    const { container } = render(
      <svg>
        <InkLine {...mockProps} />
      </svg>
    );
    
    const inkLine = container.querySelector('.ink-line');
    expect(inkLine).toBeInTheDocument();
  });

  it('应该在坐标无效时不渲染', () => {
    const { container } = render(
      <svg>
        <InkLine {...mockProps} coordinates={[]} />
      </svg>
    );
    
    const inkLine = container.querySelector('.ink-line');
    expect(inkLine).not.toBeInTheDocument();
  });

  it('应该在进度达到1时触发完成回调', () => {
    const onComplete = jest.fn();
    const { rerender } = render(
      <svg>
        <InkLine {...mockProps} progress={0} onComplete={onComplete} />
      </svg>
    );

    // 更新进度到1
    rerender(
      <svg>
        <InkLine {...mockProps} progress={1} onComplete={onComplete} />
      </svg>
    );

    // 等待动画完成
    setTimeout(() => {
      expect(onComplete).toHaveBeenCalledWith('test-route');
    }, 100);
  });

  it('应该应用自定义样式属性', () => {
    const { container } = render(
      <svg>
        <InkLine
          {...mockProps}
          strokeWidth={4}
          opacity={0.5}
          className="custom-class"
        />
      </svg>
    );
    
    const inkLine = container.querySelector('.ink-line');
    expect(inkLine).toHaveClass('custom-class');
  });
});
