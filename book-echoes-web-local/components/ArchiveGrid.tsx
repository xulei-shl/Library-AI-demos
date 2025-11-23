'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import Image from 'next/image';
import Header from './Header';

interface Month {
    id: string;
    label: string;
    vol: string;
    previewCard?: string;
    bookCount: number;
}

interface ArchiveGridProps {
    months: Month[];
}

export default function ArchiveGrid({ months }: ArchiveGridProps) {
    const router = useRouter();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [hoveredId, setHoveredId] = useState<string | null>(null);

    const handleMonthClick = (id: string) => {
        setSelectedId(id);
        // Wait for scale animation before navigating
        setTimeout(() => {
            router.push(`/${id}`);
        }, 400); // Match scale animation duration
    };

    // Calculate grid dimensions based on number of months
    // Aim for roughly square grid, prioritize 4 columns on desktop
    const getGridCols = () => {
        if (months.length <= 4) return 'grid-cols-2 md:grid-cols-4';
        if (months.length <= 8) return 'grid-cols-2 md:grid-cols-4';
        if (months.length <= 12) return 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4';
        return 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4';
    };

    return (
        <div className="relative h-screen w-screen overflow-hidden bg-[var(--background)]">
            {/* Header with Logo */}
            <Header showHomeButton={false} />

            {/* Main Grid */}
            <div className={`grid ${getGridCols()} h-full w-full`}>
                {months.map((month) => (
                    <motion.div
                        key={month.id}
                        className="relative border border-gray-300/30 overflow-hidden cursor-pointer group"
                        style={{
                            boxShadow: 'inset 0 0 8px rgba(0,0,0,0.03)'
                        }}
                        onClick={() => handleMonthClick(month.id)}
                        onMouseEnter={() => setHoveredId(month.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        whileHover={{ backgroundColor: 'rgba(0,0,0,0.02)' }}
                        transition={{ duration: 0.3 }}
                    >
                        {/* Month Label & Volume */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
                            <h2 className="font-display text-2xl md:text-3xl lg:text-4xl text-[var(--foreground)] mb-2 text-center px-4">
                                {month.label}
                            </h2>
                            <span className="font-body text-sm md:text-base text-gray-500">
                                {month.vol}
                            </span>
                            {month.bookCount > 0 && (
                                <span className="font-body text-xs text-gray-400 mt-1">
                                    {month.bookCount} 本
                                </span>
                            )}
                        </div>

                        {/* Card Peek Animation */}
                        {month.previewCard && (
                            <motion.div
                                className="absolute -bottom-20 -right-20 w-32 h-48 md:w-40 md:h-60 z-0"
                                initial={{ x: 100, y: 100, rotate: 12 }}
                                animate={{
                                    x: hoveredId === month.id ? -30 : 100,
                                    y: hoveredId === month.id ? -30 : 100,
                                    rotate: hoveredId === month.id ? 8 : 12
                                }}
                                transition={{
                                    type: "spring",
                                    stiffness: 300,
                                    damping: 30
                                }}
                            >
                                <div className="relative w-full h-full shadow-2xl rounded-sm overflow-hidden">
                                    <Image
                                        src={month.previewCard}
                                        alt={`${month.label} preview`}
                                        fill
                                        className="object-cover"
                                        sizes="(max-width: 768px) 128px, 160px"
                                    />
                                    {/* Subtle border to make card stand out */}
                                    <div className="absolute inset-0 border-2 border-white/20 rounded-sm pointer-events-none" />
                                </div>
                            </motion.div>
                        )}
                    </motion.div>
                ))}
            </div>

            {/* Scale Expansion Overlay */}
            <AnimatePresence>
                {selectedId && (
                    <motion.div
                        className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--background)]"
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        transition={{
                            duration: 0.4,
                            ease: [0.43, 0.13, 0.23, 0.96] // Custom cubic-bezier for smooth expansion
                        }}
                        style={{
                            transformOrigin: 'center center'
                        }}
                    >
                        <div className="flex flex-col items-center justify-center">
                            <motion.h2
                                className="font-display text-4xl md:text-5xl lg:text-6xl text-[var(--foreground)] mb-4"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.2, duration: 0.2 }}
                            >
                                {months.find(m => m.id === selectedId)?.label}
                            </motion.h2>
                            <motion.span
                                className="font-body text-xl md:text-2xl text-gray-500"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.25, duration: 0.2 }}
                            >
                                {months.find(m => m.id === selectedId)?.vol}
                            </motion.span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
