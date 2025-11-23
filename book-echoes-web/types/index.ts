export interface Book {
    id: string; // Barcode
    month: string;
    title: string;
    subtitle?: string;
    author: string;
    translator?: string;
    publisher: string;
    pubYear: string;
    pages: string;
    rating: string;
    callNumber: string;
    callNumberLink: string;
    doubanLink?: string;
    isbn: string;
    recommendation: string;
    reason?: string;
    summary: string;
    authorIntro: string;
    catalog: string;
    coverUrl: string;
    coverThumbnailUrl: string;
    cardImageUrl: string;
    cardThumbnailUrl?: string;
}

export interface MonthData {
    month: string; // YYYY-MM
    books: Book[];
}
