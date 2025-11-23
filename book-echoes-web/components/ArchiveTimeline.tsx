'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import Image from 'next/image';

interface Month {
    id: string;
    label: string;
    vol: string;
    previewCards: string[];
    bookCount: number;
}

interface ArchiveTimelineProps {
    months: Month[];
}

export default function ArchiveTimeline({ months }: ArchiveTimelineProps) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [hoveredId, setHoveredId] = useState<string | null>(null);

    // 按年份分组
    const groupedByYear = months.reduce((acc, month) => {
        const year = month.id.split('-')[0];
        if (!acc[year]) {
            acc[year] = [];
        }
        acc[year].push(month);
        return acc;
    }, {} as Record<string, Month[]>);

    // 获取可用年份列表(倒序)
    const availableYears = Object.keys(groupedByYear).sort((a, b) => b.localeCompare(a));

    // 从 URL 参数获取年份,如果没有则使用最新年份
    const urlYear = searchParams?.get('year');
    const [currentYear, setCurrentYear] = useState(urlYear || availableYears[0]);

    // 监听 URL 参数变化
    useEffect(() => {
        if (urlYear && availableYears.includes(urlYear)) {
            setCurrentYear(urlYear);
        }
    }, [urlYear, availableYears]);

    const displayMonths = groupedByYear[currentYear] || [];

    const handleYearChange = (year: string) => {
        setCurrentYear(year);
        router.push(`/?year=${year}`, { scroll: false });
    };

    return (
        <div className="w-full max-w-6xl mx-auto px-4">
            {/* 年份选择器 */}
            <div className="mb-8 flex items-center justify-center gap-2">
                <span className="text-sm text-gray-500 mr-2">年份:</span>
                <div className="flex gap-2 flex-wrap justify-center">
                    {availableYears.map((year) => (
                        <motion.button
                            key={year}
                            className={`px-4 py-2 rounded-lg font-medium transition-all ${
                                year === currentYear
                                    ? 'bg-[var(--foreground)] text-[var(--background)]'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            }`}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={() => handleYearChange(year)}
                        >
                            {year}
                        </motion.button>
                    ))}
                </div>
            </div>

            {/* 月份卡片网格 */}
            <motion.div
                className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                layout
            >
                <AnimatePresence mode="wait">
                    {displayMonths.map((month) => (
                        <motion.div
                            key={month.id}
                            className="relative group cursor-pointer"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.3 }}
                            onMouseEnter={() => setHoveredId(month.id)}
                            onMouseLeave={() => setHoveredId(null)}
                            onClick={() => router.push(`/${month.id}`)}
                            whileHover={{ y: -4 }}
                        >
                            {/* 卡片容器 */}
                            <div className="relative aspect-[3/4] rounded-lg overflow-hidden shadow-lg"
                                 style={{ backgroundColor: '#E8E6DC' }}>

                                {/* 纸质纹理背景 */}
                                <div className="absolute inset-0 opacity-20">
                                    <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                                        <filter id={`paper-${month.id}`}>
                                            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" result="noise" />
                                            <feDiffuseLighting in="noise" lightingColor="#8B7355" surfaceScale="1">
                                                <feDistantLight azimuth="45" elevation="60" />
                                            </feDiffuseLighting>
                                        </filter>
                                        <rect width="100%" height="100%" filter={`url(#paper-${month.id})`} opacity="0.15" />
                                    </svg>
                                </div>

                                {/* 多图拼贴预览 */}
                                {month.previewCards.length > 0 ? (
                                    <div className="absolute inset-0 flex items-center justify-center p-4">
                                        {/* 背景层 - 第3张 */}
                                        {month.previewCards.length >= 3 && (
                                            <div className="absolute w-1/3 aspect-[2/3] rounded-sm shadow-md"
                                                 style={{
                                                     transform: 'translate(35%, -10%) rotateZ(15deg)',
                                                     zIndex: 1,
                                                     opacity: 0.5
                                                 }}>
                                                <Image
                                                    src={month.previewCards[2]}
                                                    alt="Book 3"
                                                    fill
                                                    className="object-cover rounded-sm transition-transform duration-300 group-hover:scale-105"
                                                    sizes="80px"
                                                />
                                            </div>
                                        )}

                                        {/* 中间层 - 第2张 */}
                                        {month.previewCards.length >= 2 && (
                                            <div className="absolute w-1/3 aspect-[2/3] rounded-sm shadow-lg"
                                                 style={{
                                                     transform: 'translate(-35%, -5%) rotateZ(-12deg)',
                                                     zIndex: 2,
                                                     opacity: 0.65
                                                 }}>
                                                <Image
                                                    src={month.previewCards[1]}
                                                    alt="Book 2"
                                                    fill
                                                    className="object-cover rounded-sm transition-transform duration-300 group-hover:scale-105"
                                                    sizes="80px"
                                                />
                                            </div>
                                        )}

                                        {/* 主封面 - 第1张 */}
                                        <div className="relative w-1/2 aspect-[2/3] rounded-sm shadow-xl"
                                             style={{ zIndex: 10 }}>
                                            <Image
                                                src={month.previewCards[0]}
                                                alt={month.label}
                                                fill
                                                className="object-cover rounded-sm transition-transform duration-300 group-hover:scale-110"
                                                sizes="(max-width: 768px) 50vw, 150px"
                                            />
                                            <div className="absolute inset-0 rounded-sm border border-white/20" />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="absolute inset-0 bg-gradient-to-br from-gray-100 to-gray-200" />
                                )}

                                {/* 渐变遮罩 - 确保文字清晰可读 */}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-transparent pointer-events-none" />

                                {/* 文字信息层 - 提高 z-index 确保在最上层 */}
                                <div className="absolute inset-0 flex flex-col justify-end p-4 text-white pointer-events-none"
                                     style={{ zIndex: 20 }}>
                                    <h3 className="font-display text-lg md:text-xl mb-1 line-clamp-2"
                                        style={{ textShadow: '2px 2px 4px rgba(0,0,0,0.8)' }}>
                                        {month.label.replace(`${currentYear}年 `, '')}
                                    </h3>
                                    <p className="font-body text-sm text-white/90 mb-1"
                                       style={{ textShadow: '1px 1px 3px rgba(0,0,0,0.8)' }}>
                                        {month.vol}
                                    </p>
                                    {month.bookCount > 0 && (
                                        <p className="font-body text-xs text-white/70"
                                           style={{ textShadow: '1px 1px 3px rgba(0,0,0,0.8)' }}>
                                            {month.bookCount} 本
                                        </p>
                                    )}
                                </div>

                                {/* Hover 效果 */}
                                <motion.div
                                    className="absolute inset-0 bg-[var(--foreground)]/10 flex items-center justify-center pointer-events-none"
                                    style={{ zIndex: 25 }}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: hoveredId === month.id ? 1 : 0 }}
                                    transition={{ duration: 0.2 }}
                                >
                                    <span className="text-white text-sm font-medium"
                                          style={{ textShadow: '2px 2px 4px rgba(0,0,0,0.8)' }}>
                                        查看本期
                                    </span>
                                </motion.div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </motion.div>

            {/* 统计信息 */}
            <div className="mt-8 text-center text-sm text-gray-500">
                {currentYear} 年共 {displayMonths.length} 期 · 总计{' '}
                {displayMonths.reduce((sum, m) => sum + m.bookCount, 0)} 本书
            </div>
        </div>
    );
}
