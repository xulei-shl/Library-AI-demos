import { Book } from '@/types';

export function transformMetadataToBook(item: any, month: string): Book {
    return {
        id: String(item['书目条码']),
        title: item['豆瓣书名'] || '',
        subtitle: item['豆瓣副标题'] || '',
        author: item['豆瓣作者'] || '',
        translator: item['豆瓣译者'] || '',
        publisher: item['豆瓣出版社'] || '',
        pubYear: String(item['豆瓣出版年'] || ''),
        pages: String(item['豆瓣页数'] || ''),
        rating: String(item['豆瓣评分'] || ''),
        callNumber: item['索书号'] || '',
        callNumberLink: item['索书号链接'] || '',
        doubanLink: item['豆瓣链接'] || '',
        isbn: item['ISBN'] || '',
        recommendation: item['人工推荐语'] || '',
        reason: item['初评理由'] || '',
        summary: item['豆瓣内容简介'] || '',
        authorIntro: item['豆瓣作者简介'] || '',
        catalog: item['豆瓣目录'] || '',
        coverUrl: `/api/images/${month}/${item['书目条码']}/cover`,
        coverThumbnailUrl: `/api/images/${month}/${item['书目条码']}/cover-thumbnail`,
        cardImageUrl: `/api/images/${month}/${item['书目条码']}/card`,
    };
}
