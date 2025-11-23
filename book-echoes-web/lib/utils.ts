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
        title: item[FIELDS.title] || '',
        subtitle: item[FIELDS.subtitle] || '',
        author: item[FIELDS.author] || '',
        translator: item[FIELDS.translator] || '',
        publisher: item[FIELDS.publisher] || '',
        pubYear: String(item[FIELDS.publishYear] || ''),
        pages: String(item[FIELDS.pages] || ''),
        rating: String(item[FIELDS.rating] || ''),
        callNumber: item[FIELDS.callNumber] || '',
        callNumberLink: item[FIELDS.callNumberLink] || '',
        doubanLink: item[FIELDS.doubanLink] || '',
        isbn: item[FIELDS.isbn] || '',
        recommendation: item[FIELDS.recommendation] || '',
        reason: item[FIELDS.reason] || '',
        summary: item[FIELDS.summary] || '',
        authorIntro: item[FIELDS.authorIntro] || '',
        catalog: item[FIELDS.catalog] || '',
        coverUrl: resolveImageUrl(item.coverImageUrl || item[FIELDS.coverBackup], legacyCoverImagePath(month, id)),
        coverThumbnailUrl: resolveImageUrl(item.coverThumbnailUrl, legacyCoverThumbnailPath(month, id)),
        cardImageUrl: resolveImageUrl(item.cardImageUrl, legacyCardImagePath(month, id)),
        cardThumbnailUrl: resolveImageUrl(item.cardThumbnailUrl, legacyCardThumbnailPath(month, id)),
    };
}
