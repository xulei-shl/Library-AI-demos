'use client';

import { motion, useMotionValue, useTransform } from 'framer-motion';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useState, useRef } from 'react';

interface Month {
    id: string;
    label: string;
    vol: string;
    previewCards: string[];
    bookCount: number;
}

interface MagazineCoverProps {
    latestMonths: Month[];
}

export default function MagazineCover({ latestMonths }: MagazineCoverProps) {
    const router = useRouter();
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 鼠标位置追踪
    const mouseX = useMotionValue(0);
    const mouseY = useMotionValue(0);

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        mouseX.set(x);
        mouseY.set(y);
    };

    const handleMouseLeave = () => {
        mouseX.set(0);
        mouseY.set(0);
        setHoveredIndex(null);
    };

    // 根据数据数量决定布局
    const count = latestMonths.length;

    // 单卡片布局(与原设计相同)
    if (count === 1) {
        const month = latestMonths[0];
        return (
            <motion.div
                className="relative w-full max-w-md mx-auto cursor-pointer"
                onMouseEnter={() => setHoveredIndex(0)}
                onMouseLeave={() => setHoveredIndex(null)}
                onClick={() => router.push(`/${month.id}`)}
                whileHover={{ scale: 1.02 }}
                transition={{ duration: 0.3 }}
            >
                <SingleCard month={month} isHovered={hoveredIndex === 0} isLatest={true} />
            </motion.div>
        );
    }

    // 双卡片布局
    if (count === 2) {
        return (
            <div
                ref={containerRef}
                className="relative w-full max-w-4xl mx-auto"
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
            >
                <div className="grid grid-cols-2 gap-8">
                    {latestMonths.map((month, index) => (
                        <DoubleCard
                            key={month.id}
                            month={month}
                            index={index}
                            isHovered={hoveredIndex === index}
                            isLatest={index === 0}
                            onHover={() => setHoveredIndex(index)}
                            onClick={() => router.push(`/${month.id}`)}
                            mouseX={mouseX}
                            mouseY={mouseY}
                        />
                    ))}
                </div>
            </div>
        );
    }

    // 三卡片布局(最高级动效) - 优化：缩小尺寸
    return (
        <div
            ref={containerRef}
            className="relative w-full max-w-4xl mx-auto perspective-1000"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ perspective: '1500px' }}
        >
            <div className="relative flex items-center justify-center gap-4 md:gap-6">
                {latestMonths.map((month, index) => (
                    <TripleCard
                        key={month.id}
                        month={month}
                        index={index}
                        totalCount={count}
                        isHovered={hoveredIndex === index}
                        isLatest={index === 0}
                        onHover={() => setHoveredIndex(index)}
                        onClick={() => router.push(`/${month.id}`)}
                        mouseX={mouseX}
                        mouseY={mouseY}
                    />
                ))}
            </div>
        </div>
    );
}

// 单卡片组件 - 多图拼贴式封面设计
function SingleCard({ month, isHovered, isLatest }: { month: Month; isHovered: boolean; isLatest: boolean }) {
    const previewCards = month.previewCards;

    return (
        <div className="relative aspect-[3/4] rounded-lg overflow-hidden shadow-2xl"
            style={{ backgroundColor: '#E8E6DC' }}>
            {/* 纸质纹理背景 */}
            <div className="absolute inset-0 opacity-30">
                <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                    <filter id="paper-texture">
                        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" result="noise" />
                        <feDiffuseLighting in="noise" lightingColor="#8B7355" surfaceScale="1">
                            <feDistantLight azimuth="45" elevation="60" />
                        </feDiffuseLighting>
                    </filter>
                    <rect width="100%" height="100%" filter="url(#paper-texture)" opacity="0.15" />
                </svg>
            </div>

            {/* 装饰性色块 - 使用网站强调色 */}
            <div className="absolute inset-0 opacity-5">
                <div className="absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl"
                    style={{ backgroundColor: '#8B3A3A' }} />
                <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full blur-3xl"
                    style={{ backgroundColor: '#A67C52' }} />
            </div>

            {/* 书籍封面拼贴 - 多图层叠效果 */}
            {previewCards.length > 0 ? (
                <div className="absolute inset-0 flex items-center justify-center p-8">
                    {/* 根据图片数量创建拼贴布局 - 优化位置避免重叠 */}
                    {previewCards.length >= 4 && (
                        <motion.div
                            className="absolute w-1/3 aspect-[2/3] rounded-md shadow-lg"
                            initial={{ opacity: 0, scale: 0.8, x: '50%', y: '-25%', rotateZ: 18 }}
                            animate={{ opacity: 0.5, scale: 1, x: '50%', y: '-25%', rotateZ: 18 }}
                            transition={{ delay: 0.1 }}
                            style={{
                                zIndex: 1
                            }}
                        >
                            <Image
                                src={previewCards[3]}
                                alt="Book 4"
                                fill
                                className="object-cover rounded-md"
                                sizes="150px"
                            />
                        </motion.div>
                    )}

                    {previewCards.length >= 3 && (
                        <motion.div
                            className="absolute w-1/3 aspect-[2/3] rounded-md shadow-lg"
                            initial={{ opacity: 0, scale: 0.8, x: '-50%', y: '-20%', rotateZ: -15 }}
                            animate={{ opacity: 0.6, scale: 1, x: '-50%', y: '-20%', rotateZ: -15 }}
                            transition={{ delay: 0.15 }}
                            style={{
                                zIndex: 2
                            }}
                        >
                            <Image
                                src={previewCards[2]}
                                alt="Book 3"
                                fill
                                className="object-cover rounded-md"
                                sizes="150px"
                            />
                        </motion.div>
                    )}

                    {previewCards.length >= 2 && (
                        <motion.div
                            className="absolute w-2/5 aspect-[2/3] rounded-md shadow-xl"
                            initial={{ opacity: 0, scale: 0.8, x: '25%', y: '-5%', rotateZ: 8 }}
                            animate={{ opacity: 0.75, scale: 1, x: '25%', y: '-5%', rotateZ: 8 }}
                            transition={{ delay: 0.2 }}
                            style={{
                                zIndex: 3
                            }}
                        >
                            <Image
                                src={previewCards[1]}
                                alt="Book 2"
                                fill
                                className="object-cover rounded-md"
                                sizes="150px"
                            />
                        </motion.div>
                    )}

                    {/* 主封面图 - 最前面的书 */}
                    <motion.div
                        className="relative w-3/5 aspect-[2/3] rounded-md shadow-2xl"
                        initial={{ opacity: 0, scale: 0.9, rotateZ: -5 }}
                        animate={{
                            opacity: 1,
                            scale: isHovered ? 1.05 : 1,
                            rotateZ: isHovered ? 0 : -2
                        }}
                        transition={{ duration: 0.4, delay: 0.25 }}
                        style={{ zIndex: 10 }}
                    >
                        <Image
                            src={previewCards[0]}
                            alt={month.label}
                            fill
                            className="object-cover rounded-md"
                            priority
                            sizes="(max-width: 768px) 60vw, 300px"
                        />
                        {/* 边框装饰 */}
                        <div className="absolute inset-0 rounded-md border-2 border-white/10" />
                    </motion.div>
                </div>
            ) : (
                // 优雅的空状态设计
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center" style={{ color: '#8B3A3A' }}>
                        <svg className="w-24 h-24 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                        </svg>
                        <p className="font-display text-sm opacity-40">等待书籍归档</p>
                    </div>
                </div>
            )}

            {/* 半透明遮罩 - 确保文字可读，使用网站配色 */}
            <div className="absolute inset-0 pointer-events-none"
                style={{ background: 'linear-gradient(to top, rgba(44, 44, 44, 0.95) 0%, rgba(44, 44, 44, 0.7) 35%, rgba(44, 44, 44, 0.3) 55%, transparent 100%)' }} />

            {/* 文字信息层 */}
            <div className="absolute inset-0 flex flex-col justify-end p-8 pointer-events-none"
                style={{ color: '#F2F0E9', zIndex: 20 }}>
                {isLatest && (
                    <motion.div
                        className="inline-flex items-center gap-2 mb-4 w-fit"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                    >
                        <span className="px-3 py-1 backdrop-blur-sm rounded-full text-xs font-medium border"
                            style={{
                                backgroundColor: 'rgba(139, 58, 58, 0.3)',
                                borderColor: 'rgba(139, 58, 58, 0.5)',
                                color: '#F2F0E9',
                                textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
                            }}>
                            最新期
                        </span>
                    </motion.div>
                )}

                <motion.h1
                    className="font-display text-4xl md:text-5xl mb-3"
                    style={{
                        textShadow: '3px 3px 6px rgba(0,0,0,0.9)',
                        color: '#F2F0E9'
                    }}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                >
                    {month.label}
                </motion.h1>

                <motion.p
                    className="font-body text-xl md:text-2xl mb-2"
                    style={{
                        color: 'rgba(242, 240, 233, 0.9)',
                        textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
                    }}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                >
                    {month.vol}
                </motion.p>

                {month.bookCount > 0 && (
                    <motion.p
                        className="font-body text-sm"
                        style={{
                            color: 'rgba(242, 240, 233, 0.8)',
                            textShadow: '2px 2px 4px rgba(0,0,0,0.8)'
                        }}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                    >
                        收录 {month.bookCount} 本书
                    </motion.p>
                )}
            </div>

            {/* 点击提示 */}
            <motion.div
                className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap pointer-events-none"
                initial={{ opacity: 0 }}
                animate={{ opacity: isHovered ? 1 : 0 }}
                transition={{ duration: 0.2 }}
            >
                <span className="text-sm font-body" style={{ color: '#8B3A3A' }}>点击进入本期 →</span>
            </motion.div>
        </div>
    );
}

// 双卡片组件 - 多图拼贴设计
function DoubleCard({
    month,
    index,
    isHovered,
    isLatest,
    onHover,
    onClick,
    mouseX,
    mouseY
}: {
    month: Month;
    index: number;
    isHovered: boolean;
    isLatest: boolean;
    onHover: () => void;
    onClick: () => void;
    mouseX: any;
    mouseY: any;
}) {
    const rotateX = useTransform(mouseY, [-300, 300], [5, -5]);
    const rotateY = useTransform(mouseX, [-300, 300], [-5, 5]);
    const previewCards = month.previewCards;

    return (
        <motion.div
            className="relative cursor-pointer"
            onMouseEnter={onHover}
            onClick={onClick}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.6 }}
            whileHover={{ scale: 1.05, zIndex: 10 }}
            style={{
                rotateX: isHovered ? rotateX : 0,
                rotateY: isHovered ? rotateY : 0,
            }}
        >
            <div className="relative aspect-[3/4] rounded-lg overflow-hidden shadow-xl"
                style={{ backgroundColor: '#E8E6DC' }}>
                {/* 纸质纹理背景 */}
                <div className="absolute inset-0 opacity-20">
                    <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                        <filter id="paper-texture-double">
                            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" result="noise" />
                            <feDiffuseLighting in="noise" lightingColor="#8B7355" surfaceScale="1">
                                <feDistantLight azimuth="45" elevation="60" />
                            </feDiffuseLighting>
                        </filter>
                        <rect width="100%" height="100%" filter="url(#paper-texture-double)" opacity="0.15" />
                    </svg>
                </div>

                {/* 装饰性色块 */}
                <div className="absolute inset-0 opacity-5">
                    <div className="absolute top-0 right-0 w-48 h-48 rounded-full blur-3xl"
                        style={{ backgroundColor: '#8B3A3A' }} />
                    <div className="absolute bottom-0 left-0 w-32 h-32 rounded-full blur-3xl"
                        style={{ backgroundColor: '#A67C52' }} />
                </div>

                {/* 封面展示 - 多图拼贴 */}
                {previewCards.length > 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center p-6">
                        {/* 背景书籍层 */}
                        {previewCards.length >= 3 && (
                            <div className="absolute w-2/5 aspect-[2/3] rounded-md shadow-md"
                                style={{
                                    transform: 'translate(20%, -15%) rotateZ(10deg)',
                                    zIndex: 1,
                                    opacity: 0.6
                                }}>
                                <Image
                                    src={previewCards[2]}
                                    alt="Book 3"
                                    fill
                                    className="object-cover rounded-md"
                                    sizes="120px"
                                />
                            </div>
                        )}

                        {previewCards.length >= 2 && (
                            <div className="absolute w-2/5 aspect-[2/3] rounded-md shadow-lg"
                                style={{
                                    transform: 'translate(-20%, -10%) rotateZ(-6deg)',
                                    zIndex: 2,
                                    opacity: 0.75
                                }}>
                                <Image
                                    src={previewCards[1]}
                                    alt="Book 2"
                                    fill
                                    className="object-cover rounded-md"
                                    sizes="120px"
                                />
                            </div>
                        )}

                        {/* 主封面 */}
                        <motion.div
                            className="relative w-3/5 aspect-[2/3] rounded-md shadow-2xl"
                            animate={{
                                scale: isHovered ? 1.05 : 1,
                                rotateZ: isHovered ? 0 : -2
                            }}
                            style={{ zIndex: 10 }}
                        >
                            <Image
                                src={previewCards[0]}
                                alt={month.label}
                                fill
                                className="object-cover rounded-md"
                                sizes="(max-width: 768px) 50vw, 300px"
                            />
                            <div className="absolute inset-0 rounded-md border-2 border-white/10" />
                        </motion.div>
                    </div>
                ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center" style={{ color: '#8B3A3A' }}>
                            <svg className="w-16 h-16 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                            </svg>
                            <p className="font-display text-xs opacity-40">等待书籍归档</p>
                        </div>
                    </div>
                )}

                {/* 渐变遮罩 */}
                <div className="absolute inset-0 pointer-events-none"
                    style={{ background: 'linear-gradient(to top, rgba(44, 44, 44, 0.85) 0%, rgba(44, 44, 44, 0.3) 50%, transparent 100%)' }} />

                {/* 文字信息 */}
                <div className="absolute inset-0 flex flex-col justify-end p-6 pointer-events-none"
                    style={{ color: '#F2F0E9' }}>
                    {isLatest && (
                        <span className="inline-flex items-center gap-2 mb-3 w-fit px-2 py-1 backdrop-blur-sm rounded-full text-xs font-medium border"
                            style={{
                                backgroundColor: 'rgba(139, 58, 58, 0.3)',
                                borderColor: 'rgba(139, 58, 58, 0.5)'
                            }}>
                            最新期
                        </span>
                    )}
                    <h2 className="font-display text-2xl md:text-3xl mb-2"
                        style={{ textShadow: '2px 2px 4px rgba(0,0,0,0.3)' }}>
                        {month.label}
                    </h2>
                    <p className="font-body text-lg mb-1" style={{ color: 'rgba(242, 240, 233, 0.9)' }}>
                        {month.vol}
                    </p>
                    {month.bookCount > 0 && (
                        <p className="font-body text-xs" style={{ color: 'rgba(242, 240, 233, 0.8)' }}>
                            收录 {month.bookCount} 本书
                        </p>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

// 三卡片组件 - 拼贴式设计与高级动效（优化尺寸）
function TripleCard({
    month,
    index,
    totalCount,
    isHovered,
    isLatest,
    onHover,
    onClick,
    mouseX,
    mouseY
}: {
    month: Month;
    index: number;
    totalCount: number;
    isHovered: boolean;
    isLatest: boolean;
    onHover: () => void;
    onClick: () => void;
    mouseX: any;
    mouseY: any;
}) {
    const isCenter = index === 0;

    const getCardStyle = () => {
        if (totalCount === 3) {
            if (index === 0) return { scale: 1.2, rotate: 0, zIndex: 3 };
            if (index === 1) return { scale: 0.85, rotate: -8, zIndex: 1, x: -20 };
            if (index === 2) return { scale: 0.85, rotate: 8, zIndex: 1, x: 20 };
        }
        return { scale: 1, rotate: 0, zIndex: 1 };
    };

    const baseStyle = getCardStyle();
    const rotateX = useTransform(mouseY, [-300, 300], [10, -10]);
    const rotateY = useTransform(mouseX, [-300, 300], [-10, 10]);

    return (
        <motion.div
            className="relative cursor-pointer"
            onMouseEnter={onHover}
            onClick={onClick}
            initial={{ opacity: 0, y: 100, scale: 0.8 }}
            animate={{
                opacity: 1,
                y: 0,
                scale: isHovered ? baseStyle.scale * 1.1 : baseStyle.scale,
                rotate: isHovered ? 0 : baseStyle.rotate,
                x: isHovered ? 0 : baseStyle.x || 0,
                zIndex: isHovered ? 10 : baseStyle.zIndex,
            }}
            transition={{
                delay: index * 0.15,
                duration: 0.6,
                type: 'spring',
                stiffness: 100
            }}
            style={{
                rotateX: isHovered ? rotateX : 0,
                rotateY: isHovered ? rotateY : 0,
                transformStyle: 'preserve-3d',
            }}
        >
            {/* 深度阴影效果 */}
            <motion.div
                className="absolute inset-0 rounded-lg bg-black/20 blur-2xl"
                animate={{
                    scale: isHovered ? 1.1 : 0.9,
                    opacity: isHovered ? 0.5 : 0.2,
                }}
                style={{ transform: 'translateZ(-50px)' }}
            />

            <div className={`relative ${isCenter ? 'w-40 md:w-48' : 'w-32 md:w-40'} aspect-[3/4] rounded-lg overflow-hidden shadow-2xl`}
                style={{ backgroundColor: '#E8E6DC' }}>
                {/* 纸质纹理背景 */}
                <div className="absolute inset-0 opacity-15">
                    <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                        <filter id={`paper-texture-${index}`}>
                            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="4" result="noise" />
                            <feDiffuseLighting in="noise" lightingColor="#8B7355" surfaceScale="1">
                                <feDistantLight azimuth="45" elevation="60" />
                            </feDiffuseLighting>
                        </filter>
                        <rect width="100%" height="100%" filter={`url(#paper-texture-${index})`} opacity="0.15" />
                    </svg>
                </div>

                {/* 装饰性色块 */}
                <div className="absolute inset-0 opacity-5">
                    <div className={`absolute top-0 right-0 ${isCenter ? 'w-48 h-48' : 'w-32 h-32'} rounded-full blur-3xl`}
                        style={{ backgroundColor: '#8B3A3A' }} />
                    <div className={`absolute bottom-0 left-0 ${isCenter ? 'w-32 h-32' : 'w-24 h-24'} rounded-full blur-3xl`}
                        style={{ backgroundColor: '#A67C52' }} />
                </div>

                {/* 封面展示 - 多图拼贴 */}
                <motion.div
                    className="absolute inset-0"
                    animate={{
                        filter: isHovered ? 'blur(0px)' : (!isCenter ? 'blur(1px)' : 'blur(0px)'),
                    }}
                >
                    {month.previewCards.length > 0 ? (
                        <div className={`absolute inset-0 flex items-center justify-center ${isCenter ? 'p-6' : 'p-4'}`}>
                            {/* 背景书籍层 - 根据卡片大小调整 */}
                            {month.previewCards.length >= 3 && (
                                <div className={`absolute ${isCenter ? 'w-2/5' : 'w-1/3'} aspect-[2/3] rounded-md shadow-md`}
                                    style={{
                                        transform: isCenter ? 'translate(20%, -15%) rotateZ(10deg)' : 'translate(18%, -12%) rotateZ(8deg)',
                                        zIndex: 1,
                                        opacity: 0.55
                                    }}>
                                    <Image
                                        src={month.previewCards[2]}
                                        alt="Book 3"
                                        fill
                                        className="object-cover rounded-md"
                                        sizes={isCenter ? '120px' : '80px'}
                                    />
                                </div>
                            )}

                            {month.previewCards.length >= 2 && (
                                <div className={`absolute ${isCenter ? 'w-2/5' : 'w-1/3'} aspect-[2/3] rounded-md shadow-lg`}
                                    style={{
                                        transform: isCenter ? 'translate(-22%, -10%) rotateZ(-7deg)' : 'translate(-18%, -8%) rotateZ(-5deg)',
                                        zIndex: 2,
                                        opacity: 0.7
                                    }}>
                                    <Image
                                        src={month.previewCards[1]}
                                        alt="Book 2"
                                        fill
                                        className="object-cover rounded-md"
                                        sizes={isCenter ? '120px' : '80px'}
                                    />
                                </div>
                            )}

                            {/* 主封面 */}
                            <motion.div
                                className={`relative ${isCenter ? 'w-3/5' : 'w-1/2'} aspect-[2/3] rounded-md shadow-2xl`}
                                animate={{
                                    scale: isHovered ? 1.05 : 1,
                                    rotateZ: isHovered ? 0 : -2
                                }}
                                style={{ zIndex: 10 }}
                            >
                                <Image
                                    src={month.previewCards[0]}
                                    alt={month.label}
                                    fill
                                    className="object-cover rounded-md"
                                    sizes="(max-width: 768px) 50vw, 320px"
                                />
                                <div className="absolute inset-0 rounded-md border-2 border-white/10" />
                            </motion.div>
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="text-center" style={{ color: '#8B3A3A' }}>
                                <svg className={`${isCenter ? 'w-16 h-16' : 'w-12 h-12'} mx-auto mb-2 opacity-30`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                </svg>
                                <p className={`font-display ${isCenter ? 'text-xs' : 'text-[10px]'} opacity-40`}>等待书籍归档</p>
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* 渐变遮罩 */}
                <div className="absolute inset-0 pointer-events-none"
                    style={{ background: 'linear-gradient(to top, rgba(44, 44, 44, 0.85) 0%, rgba(44, 44, 44, 0.3) 50%, transparent 100%)' }} />

                {/* 光效 - 轻微提升hover时的亮度 */}
                <motion.div
                    className="absolute inset-0 pointer-events-none"
                    style={{ backgroundColor: 'rgba(242, 240, 233, 0.05)' }}
                    animate={{
                        opacity: isHovered ? 1 : 0,
                    }}
                />

                {/* 文字信息 */}
                <div className={`absolute inset-0 flex flex-col justify-end ${isCenter ? 'p-4 md:p-6' : 'p-3 md:p-4'} pointer-events-none`}
                    style={{ color: '#F2F0E9' }}>
                    {isLatest && (
                        <motion.span
                            className="inline-flex items-center gap-1 mb-1.5 w-fit px-1.5 py-0.5 backdrop-blur-sm rounded-full text-[10px] font-medium border"
                            style={{
                                backgroundColor: 'rgba(139, 58, 58, 0.3)',
                                borderColor: 'rgba(139, 58, 58, 0.5)'
                            }}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ delay: 0.3 }}
                        >
                            最新期
                        </motion.span>
                    )}
                    <motion.h2
                        className={`font-display ${isCenter ? 'text-2xl md:text-3xl' : 'text-lg md:text-xl'} mb-1.5`}
                        style={{
                            textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
                            color: '#F2F0E9'
                        }}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 + index * 0.1 }}
                    >
                        {month.label}
                    </motion.h2>
                    <motion.p
                        className={`font-body ${isCenter ? 'text-base md:text-lg' : 'text-sm md:text-base'} mb-0.5`}
                        style={{ color: 'rgba(242, 240, 233, 0.9)' }}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 + index * 0.1 }}
                    >
                        {month.vol}
                    </motion.p>
                    {month.bookCount > 0 && (
                        <motion.p
                            className={`font-body ${isCenter ? 'text-xs' : 'text-[10px]'}`}
                            style={{ color: 'rgba(242, 240, 233, 0.8)' }}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.6 + index * 0.1 }}
                        >
                            收录 {month.bookCount} 本书
                        </motion.p>
                    )}
                </div>
            </div>

            {/* 悬停提示 */}
            {isHovered && (
                <motion.div
                    className="absolute -bottom-12 left-1/2 -translate-x-1/2 whitespace-nowrap pointer-events-none"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                >
                    <span className="text-sm font-body" style={{ color: '#8B3A3A' }}>点击进入本期 →</span>
                </motion.div>
            )}
        </motion.div>
    );
}
