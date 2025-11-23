const CDN_BASE = (process.env.NEXT_PUBLIC_R2_PUBLIC_URL ?? '').replace(/\/$/, '');

function hasHttpPrefix(value: string) {
    return /^https?:\/\//i.test(value);
}

export function resolveImageUrl(primary?: string, fallback?: string) {
    const candidate = primary || fallback || '';
    if (!candidate) {
        return '';
    }
    if (hasHttpPrefix(candidate)) {
        return candidate;
    }
    if (candidate.startsWith('/')) {
        return candidate;
    }
    if (CDN_BASE) {
        return `${CDN_BASE}/${candidate.replace(/^\/+/, '')}`;
    }
    return `/${candidate.replace(/^\/+/, '')}`;
}

export function legacyCardImagePath(month: string, barcode: string) {
    return `/api/images/${month}/${barcode}/card`;
}

export function legacyCoverImagePath(month: string, barcode: string) {
    return `/api/images/${month}/${barcode}/cover`;
}

export function legacyCoverThumbnailPath(month: string, barcode: string) {
    return `/api/images/${month}/${barcode}/cover-thumbnail`;
}

export function legacyCardThumbnailPath(month: string, barcode: string) {
    return `/content/${month}/${barcode}/${barcode}_thumb.jpg`;
}
