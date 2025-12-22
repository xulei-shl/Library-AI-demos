/**
 * 个人星图导出工具
 * 参考：@docs/design/personal_constellation_module_20251215.md
 */

import type { ExportConfig } from './types';

/**
 * 导出当前视图为 PNG
 */
export async function exportToPNG(
  svgElement: SVGSVGElement,
  config: ExportConfig = { format: 'png', includeNotes: false, quality: 0.95 }
): Promise<Blob | null> {
  try {
    // 获取 SVG 尺寸
    const bbox = svgElement.getBoundingClientRect();
    const width = bbox.width;
    const height = bbox.height;

    // 序列化 SVG
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgElement);

    // 创建 Canvas
    const canvas = document.createElement('canvas');
    canvas.width = width * 2; // 2x for retina
    canvas.height = height * 2;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    // 缩放上下文
    ctx.scale(2, 2);

    // 创建图像
    const img = new Image();
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    return new Promise((resolve) => {
      img.onload = () => {
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);

        canvas.toBlob(
          (blob) => resolve(blob),
          'image/png',
          config.quality || 0.95
        );
      };

      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };

      img.src = url;
    });
  } catch (error) {
    console.error('[ShareExporter] Failed to export PNG:', error);
    return null;
  }
}

/**
 * 导出当前视图为 SVG
 */
export function exportToSVG(svgElement: SVGSVGElement): Blob | null {
  try {
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgElement);
    return new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
  } catch (error) {
    console.error('[ShareExporter] Failed to export SVG:', error);
    return null;
  }
}

/**
 * 触发下载
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * 生成文件名
 */
export function generateFilename(format: 'png' | 'svg' | 'json', authorId?: string): string {
  const timestamp = new Date().toISOString().split('T')[0];
  const author = authorId ? `_${authorId}` : '';
  return `lit_atlas${author}_${timestamp}.${format}`;
}
