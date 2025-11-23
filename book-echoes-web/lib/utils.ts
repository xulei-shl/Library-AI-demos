import { Book } from '@/types';
import {
    legacyCardImagePath,
    legacyCardThumbnailPath,
    legacyCoverImagePath,
    legacyCoverThumbnailPath,
    resolveImageUrl,
} from '@/lib/assets';

const FIELDS = {
    barcode: '书目条码',
    title: '豆瓣书名',
    subtitle: '豆瓣副标题',
    author: '豆瓣作者',
    translator: '豆瓣译者',
    publisher: '豆瓣出版社',
    publishYear: '豆瓣出版年',
    pages: '豆瓣页数',
    rating: '豆瓣评分',
    callNumber: '索书号',
    callNumberLink: '索书号链接',
    doubanLink: '豆瓣链接',
    isbn: 'ISBN',
    recommendation: '人工推荐语',
    reason: '初评理由',
    summary: '豆瓣内容简介',
    authorIntro: '豆瓣作者简介',
    catalog: '豆瓣目录',
    coverBackup: '豆瓣封面图片链接',
};

type MetadataEntry = Record<string, string | number | undefined>;

export function transformMetadataToBook(item: MetadataEntry, month: string): Book {
    const id = String(item[FIELDS.barcode]);

    return {
        id,
        month,
        title: String(item[FIELDS.title] || ''),
        subtitle: String(item[FIELDS.subtitle] || ''),
        author: String(item[FIELDS.author] || ''),
        translator: String(item[FIELDS.translator] || ''),
        publisher: String(item[FIELDS.publisher] || ''),
        pubYear: String(item[FIELDS.publishYear] || ''),
        pages: String(item[FIELDS.pages] || ''),
        rating: String(item[FIELDS.rating] || ''),
        callNumber: String(item[FIELDS.callNumber] || ''),
        callNumberLink: String(item[FIELDS.callNumberLink] || ''),
        doubanLink: String(item[FIELDS.doubanLink] || ''),
        isbn: String(item[FIELDS.isbn] || ''),
        recommendation: String(item[FIELDS.recommendation] || ''),
        reason: String(item[FIELDS.reason] || ''),
        summary: String(item[FIELDS.summary] || ''),
        authorIntro: String(item[FIELDS.authorIntro] || ''),
        catalog: String(item[FIELDS.catalog] || ''),
        coverUrl: resolveImageUrl(String(item.coverImageUrl || item[FIELDS.coverBackup] || ''), legacyCoverImagePath(month, id)),
        coverThumbnailUrl: resolveImageUrl(item.coverThumbnailUrl ? String(item.coverThumbnailUrl) : undefined, legacyCoverThumbnailPath(month, id)),
        cardImageUrl: resolveImageUrl(item.cardImageUrl ? String(item.cardImageUrl) : undefined, legacyCardImagePath(month, id)),
        cardThumbnailUrl: resolveImageUrl(item.cardThumbnailUrl ? String(item.cardThumbnailUrl) : undefined, legacyCardThumbnailPath(month, id)),
    };
}
