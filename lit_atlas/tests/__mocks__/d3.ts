/**
 * D3 Mock for Jest
 */

const createMockProjection = (): any => {
  const projection: any = jest.fn((coords: [number, number]) => {
    // 简单的线性投影模拟
    return [coords[0] * 2 + 400, 300 - coords[1] * 2] as [number, number];
  });
  
  projection.center = jest.fn().mockReturnValue(projection);
  projection.rotate = jest.fn().mockReturnValue(projection);
  projection.scale = jest.fn().mockReturnValue(projection);
  projection.translate = jest.fn().mockReturnValue(projection);
  projection.invert = jest.fn((coords: [number, number]) => {
    // 反向投影
    return [(coords[0] - 400) / 2, (300 - coords[1]) / 2] as [number, number];
  });
  
  return projection;
};

export const geoNaturalEarth1 = jest.fn(() => createMockProjection());
export const geoMercator = jest.fn(() => createMockProjection());
export const easeCubicInOut = jest.fn((t: number) => {
  // 三次缓动函数
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
});

export default {
  geoNaturalEarth1,
  geoMercator,
  easeCubicInOut,
};
