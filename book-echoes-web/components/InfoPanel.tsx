'use client';

import { motion } from 'framer-motion';
import { Book } from '@/types';
import { useStore } from '@/store/useStore';

interface InfoPanelProps {
    book: Book;
    books: Book[];
}

export default function InfoPanel({ book, books }: InfoPanelProps) {
    const { setFocusedBookId } = useStore();

    const handleNavigate = (direction: 'prev' | 'next') => {
        if (!books?.length) {
            return;
        }
        const currentIndex = books.findIndex((entry) => entry.id === book.id);
        if (currentIndex === -1) {
            return;
        }
        const delta = direction === 'next' ? 1 : -1;
        const nextIndex = (currentIndex + delta + books.length) % books.length;
        setFocusedBookId(books[nextIndex].id);
    };

    return (
        <>
            {/* Navigation Buttons - Outside panel */}
            <button
                type="button"
                aria-label="上一条书籍"
                className="fixed left-[calc(40%+2rem)] top-1/2 -translate-y-1/2 z-[121] inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-[var(--background)]/90 text-[var(--foreground)] text-2xl shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300"
                onClick={() => handleNavigate('prev')}
            >
                &larr;
            </button>
            <button
                type="button"
                aria-label="下一条书籍"
                className="fixed right-8 top-1/2 -translate-y-1/2 z-[121] inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-[var(--background)]/90 text-[var(--foreground)] text-2xl shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300"
                onClick={() => handleNavigate('next')}
            >
                &rarr;
            </button>

            {/* Three-dot Menu Button - Outside panel */}
            <div
                className="fixed top-8 right-8 z-[121] group"
            >
                {/* Three-dot button */}
                <button
                    aria-label="菜单"
                    className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-[var(--background)]/90 text-[var(--foreground)] shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] transition-all duration-300"
                >
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="5" r="2" />
                        <circle cx="12" cy="12" r="2" />
                        <circle cx="12" cy="19" r="2" />
                    </svg>
                </button>

                {/* Dropdown menu - appears on hover */}
                <div className="absolute top-14 right-0 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 flex flex-col gap-2">
                    {/* Close button */}
                    <button
                        onClick={() => setFocusedBookId(null)}
                        aria-label="关闭"
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-[var(--background)]/95 text-[var(--foreground)] shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] transition-all duration-300 whitespace-nowrap"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span className="text-sm">关闭</span>
                    </button>

                    {/* Download current book button */}
                    <button
                        onClick={async () => {
                            try {
                                // Import JSZip dynamically
                                const JSZip = (await import('jszip')).default;
                                const zip = new JSZip();

                                // Add book JSON data
                                const bookData = {
                                    书目条码: book.id,
                                    豆瓣书名: book.title,
                                    豆瓣副标题: book.subtitle,
                                    豆瓣作者: book.author,
                                    豆瓣译者: book.translator,
                                    豆瓣出版社: book.publisher,
                                    豆瓣出版年: book.pubYear,
                                    豆瓣页数: book.pages,
                                    豆瓣评分: book.rating,
                                    索书号: book.callNumber,
                                    索书号链接: book.callNumberLink,
                                    豆瓣链接: book.doubanLink,
                                    ISBN: book.isbn,
                                    人工推荐语: book.recommendation,
                                    初评理由: book.reason,
                                    豆瓣内容简介: book.summary,
                                    豆瓣作者简介: book.authorIntro,
                                    豆瓣目录: book.catalog,
                                };
                                zip.file('book_data.json', JSON.stringify(bookData, null, 2));

                                // Fetch and add barcode image
                                const barcodeResponse = await fetch(book.cardImageUrl);
                                const barcodeBlob = await barcodeResponse.blob();
                                zip.file('barcode.png', barcodeBlob);

                                // Generate and download zip
                                const content = await zip.generateAsync({ type: 'blob' });
                                const url = URL.createObjectURL(content);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `book_${book.id}.zip`;
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                URL.revokeObjectURL(url);
                            } catch (error) {
                                console.error('下载失败:', error);
                                alert('下载失败，请重试');
                            }
                        }}
                        aria-label="下载当前书籍"
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-[var(--background)]/95 text-[var(--foreground)] shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] transition-all duration-300 whitespace-nowrap"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        <span className="text-sm">下载</span>
                    </button>

                    {/* Download all metadata button */}
                    <button
                        onClick={async () => {
                            try {
                                // Extract month from book's cardImageUrl (format: /api/images/YYYY-MM/...)
                                const monthMatch = book.cardImageUrl.match(/\/api\/images\/(\d{4}-\d{2})\//);
                                if (!monthMatch) {
                                    alert('无法确定月份路径');
                                    return;
                                }
                                const month = monthMatch[1];

                                // Fetch metadata.json
                                const response = await fetch(`/content/${month}/metadata.json`);
                                const metadata = await response.json();

                                // Download as JSON file
                                const blob = new Blob([JSON.stringify(metadata, null, 2)], { type: 'application/json' });
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = `metadata_${month}.json`;
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                URL.revokeObjectURL(url);
                            } catch (error) {
                                console.error('下载失败:', error);
                                alert('下载失败，请重试');
                            }
                        }}
                        aria-label="下载全部数据"
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 bg-[var(--background)]/95 text-[var(--foreground)] shadow-[0_10px_30px_rgba(0,0,0,0.12)] backdrop-blur hover:bg-[var(--accent)] hover:text-[var(--background)] transition-all duration-300 whitespace-nowrap"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                        </svg>
                        <span className="text-sm">全部下载</span>
                    </button>
                </div>
            </div>

            <motion.div
                className="fixed right-0 top-0 bottom-28 w-[60%] bg-[var(--background)]/95 backdrop-blur-md p-12 overflow-y-auto shadow-[-10px_0_30px_rgba(0,0,0,0.05)] z-[120]"
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            >
                <div className="max-w-2xl mx-auto space-y-8 pb-32">
                    {/* Header */}
                    <div className="space-y-2">
                        <h1 className="font-display text-4xl md:text-5xl text-[var(--foreground)]">{book.title}</h1>
                        {book.subtitle && <h2 className="font-body text-xl text-gray-600">{book.subtitle}</h2>}
                    </div>

                    {/* Rating */}
                    <div className="flex items-center gap-3">
                        <div className="flex items-baseline gap-2">
                            <span className="text-3xl font-light text-[var(--foreground)]">{book.rating}</span>
                            <span className="text-sm text-gray-400">/ 10</span>
                        </div>
                        <div className="flex gap-0.5">
                            {[...Array(5)].map((_, i) => {
                                const rating = parseFloat(book.rating);
                                const filled = rating / 2 > i + 0.5;
                                const half = rating / 2 > i && rating / 2 <= i + 0.5;
                                return (
                                    <svg
                                        key={i}
                                        className="w-4 h-4"
                                        viewBox="0 0 24 24"
                                        fill={filled ? "var(--accent)" : half ? "url(#half)" : "none"}
                                        stroke="var(--accent)"
                                        strokeWidth="1.5"
                                    >
                                        <defs>
                                            <linearGradient id="half">
                                                <stop offset="50%" stopColor="var(--accent)" />
                                                <stop offset="50%" stopColor="transparent" />
                                            </linearGradient>
                                        </defs>
                                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                                    </svg>
                                );
                            })}
                        </div>
                    </div>

                    {/* Recommendation */}
                    <div className="bg-[var(--background)] border-l-4 border-[var(--accent)] p-6 my-8 relative">
                        <p className="font-accent text-xl leading-relaxed text-[var(--foreground)]">
                            {book.recommendation || book.reason || "暂无推荐语"}
                        </p>
                    </div>

                    {/* Metadata */}
                    <div className="space-y-6">
                        <div className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-4 text-sm">
                            <span className="text-gray-400 font-light">作者</span>
                            <span className="font-body text-[var(--foreground)]">{book.author}</span>

                            {book.translator && (
                                <>
                                    <span className="text-gray-400 font-light">译者</span>
                                    <span className="font-body text-[var(--foreground)]">{book.translator}</span>
                                </>
                            )}

                            <span className="text-gray-400 font-light">出版</span>
                            <span className="font-body text-[var(--foreground)]">{book.publisher} · {book.pubYear}</span>

                            <span className="text-gray-400 font-light">页数</span>
                            <span className="font-body text-[var(--foreground)]">{book.pages}</span>
                        </div>

                        {/* 索书号与豆瓣链接 */}
                        <div className="flex flex-wrap items-center gap-4 pt-4 border-t border-gray-100">
                            {book.callNumber && (
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-gray-400">馆藏</span>
                                    {book.callNumberLink ? (
                                        <a
                                            href={book.callNumberLink}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] font-mono text-xs hover:bg-[var(--accent)]/20 transition-colors"
                                        >
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                            </svg>
                                            {book.callNumber}
                                        </a>
                                    ) : (
                                        <span className="px-3 py-1.5 rounded-full bg-gray-100 font-mono text-xs text-gray-600">
                                            {book.callNumber}
                                        </span>
                                    )}
                                </div>
                            )}

                            {book.doubanLink && (
                                <a
                                    href={book.doubanLink}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 text-green-700 text-xs hover:bg-green-100 transition-colors"
                                >
                                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 18c-4.411 0-8-3.589-8-8s3.589-8 8-8 8 3.589 8 8-3.589 8-8 8z" />
                                    </svg>
                                    豆瓣页面
                                </a>
                            )}
                        </div>
                    </div>

                    {/* Deep Reading */}
                    <div className="space-y-8">
                        <section>
                            <h3 className="font-display text-lg mb-3 text-[var(--foreground)]">内容简介</h3>
                            <p className="font-body leading-loose text-gray-700 whitespace-pre-wrap">{book.summary}</p>
                        </section>

                        <section>
                            <h3 className="font-display text-lg mb-3 text-[var(--foreground)]">作者简介</h3>
                            <p className="font-body leading-loose text-gray-700">{book.authorIntro}</p>
                        </section>

                        <section>
                            <h3 className="font-display text-lg mb-3 text-[var(--foreground)]">目录</h3>
                            <details className="group">
                                <summary className="cursor-pointer inline-flex items-center gap-2 text-sm text-gray-500 hover:text-[var(--accent)] transition-colors py-2">
                                    <svg
                                        className="w-4 h-4 transition-transform group-open:rotate-90"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                    <span className="font-body">展开查看</span>
                                </summary>
                                <div className="mt-4 pl-6 border-l-2 border-gray-100">
                                    <pre className="font-body text-sm leading-loose text-gray-600 whitespace-pre-wrap font-sans">
                                        {book.catalog}
                                    </pre>
                                </div>
                            </details>
                        </section>
                    </div>
                </div>
            </motion.div>
        </>
    );
}
