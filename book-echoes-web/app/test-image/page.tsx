'use client';

import Image from 'next/image';

export default function TestImage() {
  // 直接测试外链图片
  const testImageUrl = "https://book-echoes.xulei-shl.asia/data/content/2025-09/54121111960021/54121111960021_thumb.jpg";

  console.log('环境变量 NEXT_PUBLIC_R2_PUBLIC_URL:', process.env.NEXT_PUBLIC_R2_PUBLIC_URL);

  return (
    <div className="p-8">
      <h1 className="text-2xl mb-4">图片测试页面</h1>

      <div className="mb-8">
        <h2 className="text-xl mb-2">环境变量:</h2>
        <pre className="bg-gray-100 p-4 rounded text-sm">
          NEXT_PUBLIC_R2_PUBLIC_URL: {process.env.NEXT_PUBLIC_R2_PUBLIC_URL || '(未设置)'}
        </pre>
      </div>

      <div className="mb-8">
        <h2 className="text-xl mb-2">测试1: Next.js Image (优化模式):</h2>
        <div className="relative w-64 h-96 bg-gray-200 border-2 border-red-500">
          <Image
            src={testImageUrl}
            alt="Test optimized"
            fill
            className="object-contain"
            onError={(e) => {
              console.error('Image load error (optimized):', e);
            }}
            onLoad={() => {
              console.log('Image loaded successfully (optimized)');
            }}
          />
        </div>
        <p className="text-xs text-red-600 mt-2">优化模式 (通过Next.js图片API)</p>
      </div>

      <div className="mb-8">
        <h2 className="text-xl mb-2">测试2: Next.js Image (unoptimized):</h2>
        <div className="relative w-64 h-96 bg-gray-200 border-2 border-green-500">
          <Image
            src={testImageUrl}
            alt="Test unoptimized"
            fill
            className="object-contain"
            unoptimized
            onError={(e) => {
              console.error('Image load error (unoptimized):', e);
            }}
            onLoad={() => {
              console.log('Image loaded successfully (unoptimized)');
            }}
          />
        </div>
        <p className="text-xs text-green-600 mt-2">非优化模式 (直接加载原图)</p>
      </div>

      <div className="mb-8">
        <h2 className="text-xl mb-2">测试3: 普通 img 标签:</h2>
        <img
          src={testImageUrl}
          alt="Test"
          className="w-64 border-2 border-blue-500"
        />
        <p className="text-xs text-blue-600 mt-2">原生img标签</p>
      </div>

      <div className="mb-8">
        <p className="text-sm text-gray-600">测试URL: {testImageUrl}</p>
      </div>
    </div>
  );
}
