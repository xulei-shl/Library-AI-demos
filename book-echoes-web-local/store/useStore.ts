import { create } from 'zustand';

interface BookState {
    viewMode: 'archive' | 'canvas';
    selectedMonth: string | null;
    focusedBookId: string | null;
    scatterPositions: Record<string, { x: number; y: number; rotation: number }>;

    setViewMode: (mode: 'archive' | 'canvas') => void;
    setSelectedMonth: (month: string | null) => void;
    setFocusedBookId: (id: string | null) => void;
    setScatterPosition: (id: string, pos: { x: number; y: number; rotation: number }) => void;
}

export const useStore = create<BookState>((set) => ({
    viewMode: 'archive',
    selectedMonth: null,
    focusedBookId: null,
    scatterPositions: {},

    setViewMode: (mode) => set({ viewMode: mode }),
    setSelectedMonth: (month) => set({ selectedMonth: month }),
    setFocusedBookId: (id) => set({ focusedBookId: id }),
    setScatterPosition: (id, pos) =>
        set((state) => ({
            scatterPositions: {
                ...state.scatterPositions,
                [id]: pos
            }
        })),
}));
