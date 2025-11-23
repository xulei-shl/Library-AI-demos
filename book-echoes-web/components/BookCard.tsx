'use client';

import { motion, PanInfo } from 'framer-motion';
import { Book } from '@/types';
import { useStore } from '@/store/useStore';
import { seededRandoms } from '@/lib/seededRandom';
import { useRef, useState, useEffect, useCallback, useMemo } from 'react';

const PREVIEW_WIDTH = 480;
const PREVIEW_HEIGHT = 680;
const PREVIEW_OFFSET = 16;

interface BookCardProps {
    book: Book;
    state: 'scatter' | 'focused' | 'dock';
    index?: number;
}

const CARD_WIDTH = 192;
const CARD_HEIGHT = 288;
export default function BookCard({ book, state, index = 0 }: BookCardProps) {
    const { setFocusedBookId, focusedBookId, scatterPositions, setScatterPosition } = useStore();
    const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        const updateSize = () => {
            setWindowSize({ width: window.innerWidth, height: window.innerHeight });
        };
        updateSize();
        window.addEventListener('resize', updateSize);
        return () => window.removeEventListener('resize', updateSize);
    }, []);

    const maxW = windowSize.width > 0 ? windowSize.width - CARD_WIDTH - 40 : 1720;
    const maxH = windowSize.height > 0 ? windowSize.height - CARD_HEIGHT - 40 : 780;
    const isFocused = focusedBookId === book.id;
    const isDragging = useRef(false);
    const cardRef = useRef<HTMLDivElement | null>(null);
    const [dragConstraints, setDragConstraints] = useState({ left: 0, right: 0, top: 0, bottom: 0 });
    const [currentZIndex, setCurrentZIndex] = useState(10);
    const [isHovered, setIsHovered] = useState(false);
    const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 });
    const latestScatterPosition = useRef<{ x: number; y: number; rotation: number } | null>(null);

    const updatePreviewPosition = useCallback(() => {
        if (typeof window === 'undefined' || !cardRef.current) {
            return;
        }
        const rect = cardRef.current.getBoundingClientRect();
        let left = rect.right + PREVIEW_OFFSET;
        if (window.innerWidth - rect.right < PREVIEW_WIDTH + PREVIEW_OFFSET) {
            left = rect.left - PREVIEW_WIDTH - PREVIEW_OFFSET;
        }
        let top = rect.top;
        if (window.innerHeight - rect.top < PREVIEW_HEIGHT + PREVIEW_OFFSET) {
            top = window.innerHeight - PREVIEW_HEIGHT - PREVIEW_OFFSET;
        }
        top = Math.max(PREVIEW_OFFSET, top);
        left = Math.max(PREVIEW_OFFSET, left);
        setPreviewPosition({ x: left, y: top });
    }, []);

    useEffect(() => {
        if (!isHovered) {
            return;
        }
        updatePreviewPosition();
        const handleReposition = () => updatePreviewPosition();
        window.addEventListener('scroll', handleReposition);
        window.addEventListener('resize', handleReposition);
        return () => {
            window.removeEventListener('scroll', handleReposition);
            window.removeEventListener('resize', handleReposition);
        };
    }, [isHovered, updatePreviewPosition]);

    useEffect(() => {
        if (state === 'focused') {
            setIsHovered(false);
        }
    }, [state]);

    const handleHoverStart = () => {
        setIsHovered(true);
        updatePreviewPosition();
    };

    const handleHoverEnd = () => {
        setIsHovered(false);
    };

    const handlePointerMove = (event: React.PointerEvent) => {
        if (!cardRef.current) return;

        // 检查鼠标是否真的在卡片元素上
        const rect = cardRef.current.getBoundingClientRect();
        const isInside =
            event.clientX >= rect.left &&
            event.clientX <= rect.right &&
            event.clientY >= rect.top &&
            event.clientY <= rect.bottom;

        if (!isInside && isHovered) {
            // 鼠标已经移出卡片,但悬浮状态还是 true,强制清除
            setIsHovered(false);
        } else if (isInside && isHovered) {
            updatePreviewPosition();
        }
    };

    // dock 状态下显示卡片图，scatter 状态下显示封面图
    const previewImageSrc = state === 'dock'
        ? (book.cardThumbnailUrl || book.cardImageUrl)
        : (book.cardImageUrl || book.coverUrl);

    const hoverPreview = isHovered ? (
        <motion.div
            className="pointer-events-none fixed z-[200] drop-shadow-2xl"
            style={{ left: previewPosition.x, top: previewPosition.y }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
        >
            <div
                className="rounded-2xl border border-black/5 bg-[var(--background)]/95 p-3 backdrop-blur"
                style={{ width: PREVIEW_WIDTH, height: PREVIEW_HEIGHT }}
            >
                <img
                    src={previewImageSrc}
                    alt={`${book.title} cover preview`}
                    className="w-full h-full object-contain rounded-xl bg-black/5"
                />
            </div>
        </motion.div>
    ) : null;

    const [randX, randY, randRot] = seededRandoms(book.id, 3);
    const initialScatterPosition = useMemo(() => ({
        x: randX * maxW,
        y: randY * maxH,
        rotation: randRot * 30 - 15
    }), [randX, randY, randRot, maxW, maxH]);

    const storedScatterPosition = scatterPositions[book.id];

    // Calculate drag constraints on client side only
    useEffect(() => {
        if (state === 'scatter' && typeof window !== 'undefined') {
            setDragConstraints({
                left: 0,
                right: window.innerWidth - CARD_WIDTH,
                top: 0,
                bottom: window.innerHeight - CARD_HEIGHT
            });
        }
    }, [state]);

    useEffect(() => {
        if (state === 'scatter' && !storedScatterPosition && windowSize.width > 0) {
            setScatterPosition(book.id, initialScatterPosition);
        }
    }, [state, storedScatterPosition, book.id, initialScatterPosition, setScatterPosition, windowSize.width]);

    const scatterTarget = storedScatterPosition ?? initialScatterPosition;

    useEffect(() => {
        if (state === 'scatter') {
            latestScatterPosition.current = scatterTarget;
        }
    }, [state, scatterTarget.x, scatterTarget.y, scatterTarget.rotation]);

    const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

    const handleDragStart = () => {
        isDragging.current = true;
        setCurrentZIndex(80);
        setIsHovered(false);
    };

    const handleDragEnd = (_event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
        const basePosition = latestScatterPosition.current ?? scatterTarget;
        const rightLimit = dragConstraints.right || maxW;
        const bottomLimit = dragConstraints.bottom || maxH;
        const constrained = {
            x: clamp(basePosition.x + info.offset.x, dragConstraints.left, rightLimit),
            y: clamp(basePosition.y + info.offset.y, dragConstraints.top, bottomLimit),
            rotation: basePosition.rotation
        };
        setScatterPosition(book.id, constrained);
        latestScatterPosition.current = constrained;

        // Reset dragging state after a short delay to prevent click from firing
        setTimeout(() => {
            isDragging.current = false;
            setCurrentZIndex(10);
        }, 100);
    };

    const isDock = state === 'dock';
    const isFocusedView = state === 'focused';
    const shouldRenderHoverPreview = !isFocusedView;

    let cardContent: React.ReactElement | null = null;

    const normalizedTitle = book.title.trim();
    const normalizedSubtitle = book.subtitle?.trim();
    const dockLabel = normalizedSubtitle ? `${normalizedTitle} : ${normalizedSubtitle}` : normalizedTitle;
    const dockVerticalText = dockLabel.replace(/\s+/g, '').split('').join('\n');

    if (isDock) {
        // Rotate subtle grayscale shades in the dock so each title feels distinct
        const toneSlot = index % 7;
        const dockLightness = Math.min(35 + toneSlot * 6, 70);
        const dockOpacity = Math.min(0.7 + toneSlot * 0.05, 0.98);
        const dockTextStyle = {
            color: `hsl(0 0% ${dockLightness}%)`,
            opacity: dockOpacity
        };

        cardContent = (
            <motion.div
                ref={cardRef}
                className="relative min-w-[20px] h-32 cursor-pointer transition-transform duration-200 ease-out flex items-end justify-center"
                onClick={() => setFocusedBookId(book.id)}
                whileHover={{ y: -10 }}
                onHoverStart={handleHoverStart}
                onHoverEnd={handleHoverEnd}
                onPointerMove={handlePointerMove}
                style={{ zIndex: isHovered ? 120 : undefined }}
                title={dockLabel}
                aria-label={dockLabel}
            >
                <span
                    className="font-dock text-lg tracking-[0.3em] leading-7 whitespace-pre text-center"
                    style={dockTextStyle}
                >
                    {dockVerticalText}
                </span>
            </motion.div>
        );
    } else if (isFocusedView) {
        if (isFocused) {
            cardContent = (
                <motion.div
                    layoutId={`book-${book.id}`}
                    className="absolute left-[10%] top-[10%] w-[30%] h-[80%] z-50 shadow-2xl"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1, x: 0, y: 0, rotate: 0, scale: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                    <img
                        src={book.coverUrl}
                        alt={book.title}
                        className="w-full h-full object-contain rounded-md"
                    />
                </motion.div>
            );
        } else {
            const [backgroundX, backgroundY, backgroundRot] = seededRandoms(book.id, 3);
            const viewportWidth = 1920;
            const viewportHeight = 1080;

            cardContent = (
                <motion.div
                    className="absolute w-48 h-72 opacity-5 pointer-events-none grayscale blur-sm"
                    initial={false}
                    animate={{
                        x: backgroundX * viewportWidth,
                        y: backgroundY * viewportHeight,
                        rotate: backgroundRot * 30 - 15
                    }}
                    suppressHydrationWarning
                >
                    <img
                        src={book.coverThumbnailUrl || book.coverUrl}
                        alt={book.title}
                        className="w-full h-full object-cover rounded-md"
                    />
                </motion.div>
            );
        }
    } else {
        const scatterInitial = storedScatterPosition ? {
            x: scatterTarget.x,
            y: scatterTarget.y,
            scale: 1,
            opacity: 1,
            rotate: scatterTarget.rotation
        } : {
            x: scatterTarget.x,
            y: scatterTarget.y,
            scale: 0.9,
            opacity: 0,
            rotate: scatterTarget.rotation
        };

        cardContent = (
            <motion.div
                ref={cardRef}
                layoutId={`book-${book.id}`}
                className="absolute w-48 h-72 cursor-grab active:cursor-grabbing shadow-lg hover:shadow-2xl"
                drag
                dragConstraints={dragConstraints}
                dragMomentum={false}
                dragElastic={0.1}
                whileDrag={{ scale: 1.1, rotate: 0 }}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onHoverStart={handleHoverStart}
                onHoverEnd={handleHoverEnd}
                onPointerMove={handlePointerMove}
                initial={scatterInitial}
                animate={{
                    x: scatterTarget.x,
                    y: scatterTarget.y,
                    scale: 1,
                    opacity: 1,
                    rotate: scatterTarget.rotation
                }}
                transition={{
                    type: "spring",
                    stiffness: 80,
                    damping: 15,
                    mass: 1,
                    delay: index * 0.02 // Slight stagger for burst effect
                }}
                onClick={() => {
                    // Only focus if not dragging
                    if (!isDragging.current) {
                        setFocusedBookId(book.id);
                    }
                }}
                style={{ zIndex: isHovered ? 120 : currentZIndex }}
                suppressHydrationWarning
            >
                <img
                    src={book.coverThumbnailUrl || book.coverUrl}
                    alt={book.title}
                    className="w-full h-full object-cover rounded-md pointer-events-none"
                />
            </motion.div>
        );
    }

    return (
        <>
            {shouldRenderHoverPreview && hoverPreview}
            {cardContent}
        </>
    );
}
