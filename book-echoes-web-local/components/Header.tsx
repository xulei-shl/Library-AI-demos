'use client';

import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { motion } from 'framer-motion';
import AboutOverlay from './AboutOverlay';

interface HeaderProps {
    showHomeButton?: boolean;
    aboutContent?: string;
}

export default function Header({ showHomeButton = false, aboutContent }: HeaderProps) {
    const router = useRouter();

    return (
        <header className="fixed top-0 left-0 right-0 z-50 pointer-events-none">
            <div className="flex items-center justify-between px-6 py-6 md:px-8 md:py-8">
                {/* Logo - Left */}
                <motion.div
                    className="pointer-events-auto"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="relative w-32 h-20 md:w-40 md:h-24 lg:w-48 lg:h-28 opacity-60 hover:opacity-75 transition-all duration-300">
                        <Image
                            src="/logozi_shl.jpg"
                            alt="机构Logo"
                            fill
                            className="object-contain object-left grayscale-[30%] sepia-[15%] brightness-110 contrast-90"
                            priority
                        />
                    </div>
                </motion.div>

                {/* Spacer for center alignment */}
                <div className="flex-1" />

                {/* Home Button - Center */}
                {showHomeButton && (
                    <motion.div
                        className="absolute left-1/2 -translate-x-1/2 pointer-events-auto"
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                    >
                        <button
                            onClick={() => router.push('/')}
                            className="inline-flex items-center gap-2 px-4 py-2 md:px-5 md:py-2.5 rounded-full border border-white/10 bg-[var(--background)]/90 text-[var(--foreground)] text-sm md:text-base font-body shadow-[0_10px_30px_rgba(0,0,0,0.08)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300"
                            aria-label="返回首页"
                        >
                            <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                                />
                            </svg>
                            <span>首页</span>
                        </button>
                    </motion.div>
                )}

                {/* About Button - Right */}
                {aboutContent && (
                    <motion.div
                        className="pointer-events-auto"
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                    >
                        <AboutOverlay content={aboutContent} />
                    </motion.div>
                )}

                {/* Right spacer to balance layout when no about button */}
                {!aboutContent && <div className="flex-1" />}
            </div>
        </header>
    );
}
