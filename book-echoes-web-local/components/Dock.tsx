'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Book } from '@/types';
import BookCard from './BookCard';
import { useStore } from '@/store/useStore';

interface DockProps {
    books: Book[];
}

export default function Dock({ books }: DockProps) {
    const { focusedBookId } = useStore();
    const showDock = !focusedBookId;

    return (
        <AnimatePresence>
            {showDock && (
                <motion.div
                    className="font-dock pointer-events-none fixed bottom-3 left-3 max-w-[38vw] flex flex-wrap justify-start gap-2.5 z-50"
                    initial={{ y: 100, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    exit={{ y: 80, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 140, damping: 20 }}
                >
                    {books.map((book, index) => (
                        <div key={book.id} className="pointer-events-auto">
                            <BookCard book={book} state="dock" index={index} />
                        </div>
                    ))}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
