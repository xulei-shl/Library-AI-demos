import { promises as fs } from 'fs';
import path from 'path';
import Canvas from '@/components/Canvas';
import { Book } from '@/types';
import { transformMetadataToBook } from '@/lib/utils';

interface PageProps {
    params: Promise<{
        month: string;
    }>;
}

// Function to get data for a specific month
async function getMonthData(month: string): Promise<Book[]> {
    const filePath = path.join(process.cwd(), 'public', 'content', month, 'metadata.json');

    try {
        const fileContents = await fs.readFile(filePath, 'utf8');
        const data = JSON.parse(fileContents);

        return data.map((item: any) => transformMetadataToBook(item, month));
    } catch (error) {
        console.error(`Error loading data for month ${month}:`, error);
        return [];
    }
}

export default async function MonthPage({ params }: PageProps) {
    const { month } = await params;
    const books = await getMonthData(month);

    if (!books || books.length === 0) {
        return (
            <div className="flex items-center justify-center h-screen bg-[var(--background)] text-[var(--foreground)]">
                <h1 className="font-display text-2xl">Month not found or empty</h1>
            </div>
        );
    }

    return <Canvas books={books} month={month} />;
}

export async function generateStaticParams() {
    const contentDir = path.join(process.cwd(), 'public', 'content');
    try {
        const months = await fs.readdir(contentDir);
        return months.filter(m => !m.startsWith('.')).map((month) => ({
            month,
        }));
    } catch (e) {
        return [];
    }
}
