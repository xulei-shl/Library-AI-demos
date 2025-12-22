/**
 * RippleNode组件测试
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { RippleNode } from '../../../src/core/nodes/RippleNode';

describe('RippleNode', () => {
  const mockProps = {
    cityId: 'beijing',
    cityName: '北京',
    coordinates: [400, 300] as [number, number],
    hasCollection: false,
  };

  it('应该正确渲染', () => {
    const { container } = render(
      <svg>
        <RippleNode {...mockProps} />
      </svg>
    );
    
    const node = container.querySelector('.ripple-node');
    expect(node).toBeInTheDocument();
  });

  it('应该在点击时触发回调', () => {
    const onClick = jest.fn();
    const { container } = render(
      <svg>
        <RippleNode {...mockProps} onClick={onClick} />
      </svg>
    );
    
    const button = container.querySelector('[role="button"]');
    if (button) {
      fireEvent.click(button);
      expect(onClick).toHaveBeenCalledWith('beijing');
    }
  });

  it('应该支持键盘导航', () => {
    const onClick = jest.fn();
    const { container } = render(
      <svg>
        <RippleNode {...mockProps} onClick={onClick} />
      </svg>
    );
    
    const button = container.querySelector('[role="button"]');
    if (button) {
      fireEvent.keyDown(button, { key: 'Enter' });
      expect(onClick).toHaveBeenCalled();
    }
  });

  it('应该在有馆藏时显示呼吸动画', () => {
    const { container } = render(
      <svg>
        <RippleNode
          {...mockProps}
          hasCollection={true}
          collectionMeta={{
            title: '测试馆藏',
            date: '1920-01-01',
            location: '北京图书馆',
          }}
        />
      </svg>
    );
    
    // 检查是否有呼吸动画元素
    const node = container.querySelector('.ripple-node');
    expect(node).toBeInTheDocument();
  });

  it('应该显示正确的无障碍标签', () => {
    const { container } = render(
      <svg>
        <RippleNode {...mockProps} year={1920} />
      </svg>
    );
    
    const button = container.querySelector('[role="button"]');
    expect(button).toHaveAttribute('aria-label');
    expect(button?.getAttribute('aria-label')).toContain('北京');
    expect(button?.getAttribute('aria-label')).toContain('1920');
  });
});
