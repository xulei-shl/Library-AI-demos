'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import clsx from 'clsx';

interface AboutOverlayProps {
    content: string;
    triggerClassName?: string;
}

const markdownComponents: Components = {
    h1: (props) => (
        <h1
            className="font-display text-4xl md:text-5xl text-[var(--foreground)] tracking-wide mb-6"
            {...props}
        />
    ),
    h2: (props) => (
        <h2
            className="font-display text-2xl md:text-3xl text-[var(--foreground)] mt-10 mb-4 border-l-4 border-[var(--accent)] pl-4"
            {...props}
        />
    ),
    h3: (props) => (
        <h3
            className="font-display text-xl text-[var(--foreground)] mt-8 mb-3"
            {...props}
        />
    ),
    p: (props) => (
        <p
            className="font-body leading-relaxed text-gray-700 mb-4 whitespace-pre-wrap"
            {...props}
        />
    ),
    ul: (props) => (
        <ul className="list-disc list-inside space-y-2 text-gray-700 mb-6" {...props} />
    ),
    ol: (props) => (
        <ol className="list-decimal list-inside space-y-2 text-gray-700 mb-6" {...props} />
    ),
    li: (props) => (
        <li className="font-body leading-relaxed text-gray-700" {...props} />
    ),
    hr: () => <div className="my-10 border-t border-dashed border-gray-200" />,
    strong: (props) => (
        <strong className="text-[var(--foreground)] font-semibold" {...props} />
    ),
    em: (props) => (
        <em className="text-[var(--accent)] not-italic" {...props} />
    ),
    blockquote: (props) => (
        <blockquote
            className="border-l-4 border-[var(--accent)]/40 pl-4 italic text-gray-600 my-6"
            {...props}
        />
    ),
    table: (props) => (
        <div className="overflow-x-auto rounded-2xl border border-gray-100 my-6">
            <table className="min-w-full divide-y divide-gray-200" {...props} />
        </div>
    ),
    thead: (props) => (
        <thead className="bg-[var(--background)]/60 text-[var(--foreground)] uppercase text-xs tracking-widest" {...props} />
    ),
    tbody: (props) => <tbody className="divide-y divide-gray-100" {...props} />,
    th: (props) => (
        <th className="px-4 py-3 text-left font-medium text-sm" {...props} />
    ),
    td: (props) => (
        <td className="px-4 py-3 text-sm text-gray-700 align-top" {...props} />
    ),
    code: ({ inline, className, children, ...props }: any) => {
        if (inline) {
            return (
                <code
                    className={clsx(
                        'font-mono text-sm px-1.5 py-0.5 rounded bg-gray-100 text-[var(--accent)]',
                        className
                    )}
                    {...props}
                >
                    {children}
                </code>
            );
        }

        return (
            <pre className={clsx('bg-gray-50 rounded-2xl p-4 overflow-x-auto text-sm text-gray-700 my-6', className)}>
                <code {...props}>{children}</code>
            </pre>
        );
    }
};

export default function AboutOverlay({ content, triggerClassName }: AboutOverlayProps) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            <button
                type="button"
                onClick={() => setIsOpen(true)}
                className={clsx(
                    'inline-flex items-center gap-2 px-5 py-2.5 rounded-full border border-white/10 bg-[var(--background)]/90 text-[var(--foreground)] text-sm md:text-base font-body shadow-[0_10px_30px_rgba(0,0,0,0.08)] backdrop-blur pointer-events-auto hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300',
                    triggerClassName
                )}
                aria-haspopup="dialog"
                aria-expanded={isOpen}
                aria-controls="about-overlay"
            >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.8}
                        d="M12 6v6m0 2v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                </svg>
                <span>关于</span>
            </button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            className="fixed inset-0 bg-[var(--background)]/80 backdrop-blur-sm z-[140]"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsOpen(false)}
                        />
                        <motion.div
                            id="about-overlay"
                            role="dialog"
                            aria-modal="true"
                            className="fixed inset-x-4 md:inset-x-16 lg:inset-x-24 top-12 bottom-12 bg-[var(--background)]/95 backdrop-blur-xl rounded-3xl border border-white/10 p-6 md:p-10 overflow-hidden shadow-[0_30px_60px_rgba(0,0,0,0.25)] z-[150]"
                            initial={{ opacity: 0, y: 40 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 40 }}
                            transition={{ type: 'spring', damping: 20, stiffness: 200 }}
                        >
                            <div className="flex items-start justify-between gap-6 mb-6 md:mb-10">
                                <div>
                                    <p className="text-sm tracking-[0.4em] uppercase text-gray-400 mb-2">About</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setIsOpen(false)}
                                    className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-[var(--background)]/80 text-[var(--foreground)] text-2xl hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300"
                                    aria-label="关闭关于介绍"
                                >
                                    ×
                                </button>
                            </div>

                            <div className="relative h-full">
                                <div className="about-overlay-scroll absolute inset-0 overflow-y-auto pr-3 pb-16">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={markdownComponents}
                                    >
                                        {content}
                                    </ReactMarkdown>
                                </div>

                                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[var(--background)] to-transparent pointer-events-none" />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </>
    );
}
