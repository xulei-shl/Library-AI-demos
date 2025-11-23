import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ month: string; id: string; type: string }> }
) {
    const { month, id, type } = await params;

    let filePath = '';
    let contentType = '';

    if (type === 'card' || type === 'thumbnail') {
        filePath = path.join(process.cwd(), 'public', 'content', month, id, `${id}.png`);
        contentType = 'image/png';
    } else if (type === 'cover') {
        filePath = path.join(process.cwd(), 'public', 'content', month, id, 'pic', 'cover.jpg');
        contentType = 'image/jpeg';
    } else if (type === 'cover-thumbnail') {
        filePath = path.join(process.cwd(), 'public', 'content', month, id, 'pic', 'cover_thumb.jpg');
        contentType = 'image/jpeg';
    } else {
        return new NextResponse('Invalid image type', { status: 400 });
    }

    try {
        const imageBuffer = await fs.promises.readFile(filePath);
        return new NextResponse(imageBuffer, {
            headers: {
                'Content-Type': contentType,
                'Cache-Control': 'public, max-age=31536000, immutable',
            },
        });
    } catch (error) {
        console.error(`Error serving image ${filePath}:`, error);
        return new NextResponse('Image not found', { status: 404 });
    }
}
