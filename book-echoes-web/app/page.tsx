import MagazineCover from '@/components/MagazineCover';
import ArchiveTimeline from '@/components/ArchiveTimeline';
import Header from '@/components/Header';
import HomeBackground from '@/components/HomeBackground';
import { promises as fs } from 'fs';
import path from 'path';
import { legacyCardThumbnailPath, resolveImageUrl } from '@/lib/assets';

export const revalidate = 3600;
export const dynamic = 'force-static';

async function getMonths() {
  const contentDir = path.join(process.cwd(), 'public', 'content');
  try {
    const entries = await fs.readdir(contentDir, { withFileTypes: true });
    const months = entries
      .filter(entry => entry.isDirectory() && !entry.name.startsWith('.'))
      .map(entry => entry.name)
      .sort((a, b) => b.localeCompare(a)); // Newest first

    const monthsWithData = await Promise.all(months.map(async (id, index) => {
      // Format: 2025-09 -> 二零二五年 九月
      const [year, month] = id.split('-');
      const yearCN = year.split('').map(d => '零一二三四五六七八九'[parseInt(d)]).join('');
      const monthCN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二'][parseInt(month) - 1];

      // Try to get preview cards and book count from metadata
      let previewCards: string[] = [];
      let bookCount = 0;

      try {
        const metadataPath = path.join(contentDir, id, 'metadata.json');
        const metadataContent = await fs.readFile(metadataPath, 'utf8');
        const books = JSON.parse(metadataContent);
        bookCount = books.length;

        // Randomly select 4-6 books for collage preview to create variety
        const numToShow = Math.min(books.length, Math.floor(Math.random() * 3) + 4); // 4-6 books
        const shuffled = [...books].sort(() => Math.random() - 0.5);
        const booksToShow = shuffled.slice(0, numToShow);

        previewCards = booksToShow.map((book: { '书目条码': string; cardThumbnailUrl?: string; cardImageUrl?: string }) => {
          const bookId = String(book['书目条码']);
          const candidate = book.cardThumbnailUrl || book.cardImageUrl;
          return resolveImageUrl(candidate, legacyCardThumbnailPath(id, bookId));
        });
      } catch (e) {
        console.warn(`Could not load metadata for ${id}:`, e);
      }

      return {
        id,
        label: `${yearCN}年 ${monthCN}月`,
        vol: `Vol. ${months.length - index}`,
        previewCards,
        bookCount
      };
    }));

    return monthsWithData;
  } catch (e) {
    console.error("Error reading content directory:", e);
    return [];
  }
}

async function getAboutContent() {
  const aboutPath = path.join(process.cwd(), 'public', 'About.md');
  try {
    return await fs.readFile(aboutPath, 'utf8');
  } catch (e) {
    console.warn('Failed to load About content:', e);
    return '';
  }
}


export default async function Home() {
  const months = await getMonths();
  const latestMonths = months.slice(0, 3); // 最新3期
  const archiveMonths = months.slice(3); // 其余期刊
  const aboutContent = await getAboutContent();

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--background)]">
      <HomeBackground
        institutionName="那些被悄悄归还的一本好书"
        projectName="书海回响"
      />
      <div className="noise-overlay" />

      {/* Header with About button */}
      <Header showHomeButton={false} aboutContent={aboutContent} />

      {/* 主内容区域 - 优化布局与间距 */}
      <div className="relative z-10 pt-24 md:pt-32 pb-20 md:pb-28 px-4">
        {/* 最新期封面展示 */}
        {latestMonths.length > 0 && (
          <section className="magazine-cover-wrapper mb-16 md:mb-24">
            <MagazineCover latestMonths={latestMonths} />
          </section>
        )}

        {/* 优雅的分隔线 */}
        {archiveMonths.length > 0 && (
          <div className="max-w-6xl mx-auto mb-16 md:mb-20">
            <div className="flex items-center gap-6 md:gap-8">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent opacity-50" />
              <h2 className="font-display text-sm md:text-base tracking-[0.4em] text-gray-400 uppercase px-2">
                往期回顾
              </h2>
              <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent opacity-50" />
            </div>
          </div>
        )}

        {/* 往期归档时间线 */}
        {archiveMonths.length > 0 && (
          <section>
            <ArchiveTimeline months={archiveMonths} />
          </section>
        )}
      </div>
    </main>
  );
}
