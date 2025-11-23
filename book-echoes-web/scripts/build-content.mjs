#!/usr/bin/env node

/**
 * Build Content Script
 * 
 * This script processes source data from sources_data/[month] and generates
 * structured content in content/[month] for the frontend to consume.
 * 
 * Usage: node scripts/build-content.mjs [YYYY-MM]
 * Example: node scripts/build-content.mjs 2025-09
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import xlsx from 'xlsx';
import sharp from 'sharp';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const ENV_FILES = ['.env.local', '.env'];

// Configuration
const SOURCES_DIR = path.join(PROJECT_ROOT, 'sources_data');
const CONTENT_DIR = path.join(PROJECT_ROOT, 'public', 'content');
const PASS_COLUMN = '人工评选';
const PASS_VALUE = '通过';
const BARCODE_COLUMN = '书目条码';
const CALL_NUMBER_URL_TEMPLATE = 'https://vufind.library.sh.cn/Search/Results?searchtype=vague&lookfor={call_number}&type=CallNumber';
const CALL_NUMBER_URL_ENCODING = {
    '/': '%2F',
    '#': '%23',
    '*': '%2A',
    ' ': '%20',
    '+': '%2B',
    '=': '%3D',
    '?': '%3F',
    '&': '%26'
};

/**
 * Main execution function
 */
async function main() {
    const month = process.argv[2];

    if (!month || !/^\d{4}-\d{2}$/.test(month)) {
        console.error('❌ Error: Please provide a valid month parameter (YYYY-MM)');
        console.error('   Example: node scripts/build-content.mjs 2025-09');
        process.exit(1);
    }

    console.log(`\n📚 Building content for ${month}...\n`);

    try {
        await loadEnvFiles();
        const r2Config = createR2Config();
        // Step 1: Clean target directory
        await cleanTargetDirectory(month);

        // Step 2: Read and filter Excel data
        const books = await readAndFilterExcel(month);
        console.log(`✅ Found ${books.length} books marked as "${PASS_VALUE}"\n`);

        // Step 3: Migrate resources for each book
        const assetsMap = await migrateResources(month, books, r2Config);

        // Step 4: Generate metadata Excel file with filtered data
        await copyMetadata(month, books, assetsMap);

        console.log(`\n✨ Build completed successfully for ${month}!\n`);
    } catch (error) {
        console.error(`\n❌ Build failed:`, error.message);
        console.error(error.stack);
        process.exit(1);
    }
}

/**
 * Step 1: Clean the target content directory
 */
async function cleanTargetDirectory(month) {
    const targetDir = path.join(CONTENT_DIR, month);

    try {
        await fs.rm(targetDir, { recursive: true, force: true });
        console.log(`🧹 Cleaned directory: content/${month}`);
    } catch (error) {
        // Directory might not exist, which is fine
        console.log(`🧹 Target directory doesn't exist yet: content/${month}`);
    }

    // Create fresh directory
    await fs.mkdir(targetDir, { recursive: true });
    console.log(`📁 Created directory: content/${month}\n`);
}

/**
 * Step 2: Read Excel file and filter for approved books
 */
async function readAndFilterExcel(month) {
    const sourceDir = path.join(SOURCES_DIR, month);

    // Find the Excel file
    const files = await fs.readdir(sourceDir);
    const excelFile = files.find(f => f.endsWith('.xlsx'));

    if (!excelFile) {
        throw new Error(`No .xlsx file found in sources_data/${month}`);
    }

    const excelPath = path.join(sourceDir, excelFile);
    console.log(`📖 Reading Excel file: ${excelFile}`);

    // Read the Excel file
    const workbook = xlsx.readFile(excelPath);
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];

    // Convert to JSON
    const data = xlsx.utils.sheet_to_json(worksheet);

    // Filter for approved books
    const approvedBooks = data.filter(row => row[PASS_COLUMN] === PASS_VALUE);

    // Validate that all approved books have barcodes
    const invalidBooks = approvedBooks.filter(book => !book[BARCODE_COLUMN]);
    if (invalidBooks.length > 0) {
        console.warn(`⚠️  Warning: ${invalidBooks.length} approved books are missing barcodes and will be skipped`);
    }

    return approvedBooks.filter(book => book[BARCODE_COLUMN]);
}

/**
 * Step 3: Migrate resources (images) for each book
 */
async function migrateResources(month, books, r2Config) {
    const sourceDir = path.join(SOURCES_DIR, month);
    const targetDir = path.join(CONTENT_DIR, month);

    let successCount = 0;
    let errorCount = 0;
    const assetsMap = new Map();

    for (const book of books) {
        const barcode = String(book[BARCODE_COLUMN]);
        const bookSourceDir = path.join(sourceDir, barcode);
        const bookTargetDir = path.join(targetDir, barcode);
        const picTargetDir = path.join(bookTargetDir, 'pic');
        const assetRecord = {
            cardImageUrl: '',
            cardThumbnailUrl: '',
            coverImageUrl: '',
            coverThumbnailUrl: '',
            originalImageUrl: '',          // 原始图片（无后缀）
            originalThumbnailUrl: ''       // 原始图片缩略图
        };

        try {
            try {
                await fs.access(bookSourceDir);
            } catch {
                console.warn(`??  Skipping ${barcode}: Source directory not found`);
                errorCount++;
                continue;
            }

            await fs.mkdir(bookTargetDir, { recursive: true });
            await fs.mkdir(picTargetDir, { recursive: true });

            const cardSource = path.join(bookSourceDir, `${barcode}-S.png`);
            const cardTarget = path.join(bookTargetDir, `${barcode}.png`);
            let cardExists = false;

            try {
                await fs.copyFile(cardSource, cardTarget);
                cardExists = true;
            } catch {
                console.warn(`??  Warning: Card image not found for ${barcode}`);
            }

            // 处理原始图片（无后缀）
            const originalSource = path.join(bookSourceDir, `${barcode}.png`);
            const originalTarget = path.join(bookTargetDir, `${barcode}_original.png`);
            let originalExists = false;

            try {
                await fs.copyFile(originalSource, originalTarget);
                originalExists = true;
            } catch {
                console.warn(`??  Warning: Original image not found for ${barcode}`);
            }

            const coverSource = path.join(bookSourceDir, 'pic', 'cover.jpg');
            const coverTarget = path.join(picTargetDir, 'cover.jpg');
            let coverExists = false;

            try {
                await fs.copyFile(coverSource, coverTarget);
                coverExists = true;
            } catch {
                console.warn(`??  Warning: Cover image not found for ${barcode}`);
            }

            const qrcodeSource = path.join(bookSourceDir, 'pic', 'qrcode.png');
            const qrcodeTarget = path.join(picTargetDir, 'qrcode.png');

            try {
                await fs.copyFile(qrcodeSource, qrcodeTarget);
            } catch {
                console.warn(`??  Warning: QR code not found for ${barcode}`);
            }

            let cardThumbExists = false;
            const cardThumbnailTarget = path.join(bookTargetDir, `${barcode}_thumb.jpg`);
            if (cardExists) {
                try {
                    await sharp(cardSource)
                        .resize(400, null, { withoutEnlargement: true })
                        .jpeg({ quality: 85 })
                        .toFile(cardThumbnailTarget);
                    cardThumbExists = true;
                } catch (error) {
                    console.warn(`??  Warning: Could not generate card thumbnail for ${barcode}`);
                }
            }

            let coverThumbExists = false;
            const coverThumbnailTarget = path.join(picTargetDir, 'cover_thumb.jpg');
            if (coverExists) {
                try {
                    await sharp(coverSource)
                        .resize(400, null, { withoutEnlargement: true })
                        .jpeg({ quality: 85 })
                        .toFile(coverThumbnailTarget);
                    coverThumbExists = true;
                } catch (error) {
                    console.warn(`??  Warning: Could not generate cover thumbnail for ${barcode}`);
                }
            }

            // 生成原始图片的缩略图
            let originalThumbExists = false;
            const originalThumbnailTarget = path.join(bookTargetDir, `${barcode}_original_thumb.jpg`);
            if (originalExists) {
                try {
                    await sharp(originalSource)
                        .resize(400, null, { withoutEnlargement: true })
                        .jpeg({ quality: 85 })
                        .toFile(originalThumbnailTarget);
                    originalThumbExists = true;
                } catch (error) {
                    console.warn(`??  Warning: Could not generate original thumbnail for ${barcode}`);
                }
            }

            await attachAssetUrls({
                month,
                barcode,
                r2Config,
                assetRecord,
                cardExists,
                coverExists,
                cardThumbExists,
                coverThumbExists,
                originalExists,
                originalThumbExists,
                paths: {
                    cardTarget,
                    cardThumbnailTarget,
                    coverTarget,
                    coverThumbnailTarget,
                    originalTarget,
                    originalThumbnailTarget
                }
            });

            successCount++;
            assetsMap.set(barcode, assetRecord);
            console.log(`Processed: ${barcode}`);
        } catch (error) {
            console.error(`Error processing ${barcode}:`, error.message);
            errorCount++;
        }
    }

    console.log(`
?? Migration Summary:`);
    console.log(`   ??Success: ${successCount}`);
    console.log(`   ??Errors: ${errorCount}`);

    return assetsMap;
}


/**
 * Generate encoded call number link for catalog lookup
 */
function buildCallNumberLink(callNumberRaw) {
    if (!callNumberRaw) {
        return '';
    }
    const normalized = String(callNumberRaw).trim();
    if (!normalized) {
        return '';
    }
    const encoded = Array.from(normalized)
        .map(char => CALL_NUMBER_URL_ENCODING[char] ?? char)
        .join('');
    return CALL_NUMBER_URL_TEMPLATE.replace('{call_number}', encoded);
}

/**
 * Step 4: Generate metadata JSON file with only filtered approved books
 * Only includes fields needed by the frontend to optimize performance
 */
async function copyMetadata(month, books, assetsMap = new Map()) {
    const targetDir = path.join(CONTENT_DIR, month);
    const targetJson = path.join(targetDir, 'metadata.json');

    // Define fields needed by frontend (based on PRD 4.2)
    const frontendFields = [
        '书目条码',      // Unique ID / Image index
        '豆瓣书名',      // Main title
        '豆瓣副标题',    // Subtitle
        '豆瓣原作名',    // Original title
        '豆瓣作者',      // Author
        '豆瓣译者',      // Translator
        '豆瓣出版社',    // Publisher
        '豆瓣出版年',    // Publication year
        '豆瓣页数',      // Page count
        '豆瓣评分',      // Rating
        '豆瓣评价人数',  // Number of ratings
        '索书号',        // Call number (important business data)
        'ISBN',          // ISBN
        '人工推荐语',    // Manual recommendation (Priority 1)
        '初评理由',      // Initial review reason (Priority 2)
        '豆瓣内容简介',  // Content description
        '豆瓣作者简介',  // Author bio
        '豆瓣目录',      // Table of contents
        '豆瓣链接',      // Douban link
        '豆瓣封面图片链接', // Cover image link (backup)
        '豆瓣定价',      // Price
        '豆瓣装帧',      // Binding
        '豆瓣丛书',      // Series
        '豆瓣出品方',     // Producer
        '索书号链接'     // Generated call number search link
    ];

    // Filter books to only include frontend-needed fields
    const optimizedBooks = books.map(book => {
        const filtered = {};
        frontendFields.forEach(field => {
            if (book[field] !== undefined && book[field] !== null && book[field] !== '') {
                filtered[field] = book[field];
            }
        });
        if (filtered['索书号']) {
            const callNumberLink = buildCallNumberLink(filtered['索书号']);
            if (callNumberLink) {
                filtered['索书号链接'] = callNumberLink;
            }
        }
        const barcode = String(book[BARCODE_COLUMN]);
        const assets = assetsMap.get(barcode);

        if (assets?.cardImageUrl) {
            filtered.cardImageUrl = assets.cardImageUrl;
        }
        if (assets?.cardThumbnailUrl) {
            filtered.cardThumbnailUrl = assets.cardThumbnailUrl;
        }
        if (assets?.coverImageUrl) {
            filtered.coverImageUrl = assets.coverImageUrl;
        }
        if (assets?.coverThumbnailUrl) {
            filtered.coverThumbnailUrl = assets.coverThumbnailUrl;
        }
        if (assets?.originalImageUrl) {
            filtered.originalImageUrl = assets.originalImageUrl;
        }
        if (assets?.originalThumbnailUrl) {
            filtered.originalThumbnailUrl = assets.originalThumbnailUrl;
        }

        return filtered;
    });

    // Write the filtered data to JSON file
    await fs.writeFile(targetJson, JSON.stringify(optimizedBooks, null, 2), 'utf-8');

    const originalSize = JSON.stringify(books).length;
    const optimizedSize = JSON.stringify(optimizedBooks).length;
    const reduction = ((1 - optimizedSize / originalSize) * 100).toFixed(1);

    console.log(`\n📋 Generated metadata.json with ${books.length} approved books`);
    console.log(`   📦 Size reduction: ${reduction}% (${(originalSize / 1024).toFixed(1)}KB → ${(optimizedSize / 1024).toFixed(1)}KB)`);
}

async function attachAssetUrls({
    month,
    barcode,
    r2Config,
    assetRecord,
    cardExists,
    coverExists,
    cardThumbExists,
    coverThumbExists,
    originalExists,
    originalThumbExists,
    paths
}) {
    if (cardExists) {
        const relativePath = buildLocalContentPath(month, barcode, `${barcode}.png`);
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.cardTarget,
            buildR2Key(r2Config, 'content', month, barcode, `${barcode}.png`),
            'image/png'
        );
        assetRecord.cardImageUrl = selectAssetUrl(remoteUrl, relativePath);
    }

    if (cardThumbExists) {
        const relativePath = buildLocalContentPath(month, barcode, `${barcode}_thumb.jpg`);
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.cardThumbnailTarget,
            buildR2Key(r2Config, 'content', month, barcode, `${barcode}_thumb.jpg`),
            'image/jpeg'
        );
        assetRecord.cardThumbnailUrl = selectAssetUrl(remoteUrl, relativePath);
    }

    if (coverExists) {
        const relativePath = buildLocalContentPath(month, barcode, 'pic', 'cover.jpg');
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.coverTarget,
            buildR2Key(r2Config, 'content', month, barcode, 'pic/cover.jpg'),
            'image/jpeg'
        );
        assetRecord.coverImageUrl = selectAssetUrl(remoteUrl, relativePath);
    }

    if (coverThumbExists) {
        const relativePath = buildLocalContentPath(month, barcode, 'pic', 'cover_thumb.jpg');
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.coverThumbnailTarget,
            buildR2Key(r2Config, 'content', month, barcode, 'pic/cover_thumb.jpg'),
            'image/jpeg'
        );
        assetRecord.coverThumbnailUrl = selectAssetUrl(remoteUrl, relativePath);
    }

    // 上传原始图片
    if (originalExists) {
        const relativePath = buildLocalContentPath(month, barcode, `${barcode}_original.png`);
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.originalTarget,
            buildR2Key(r2Config, 'content', month, barcode, `${barcode}_original.png`),
            'image/png'
        );
        assetRecord.originalImageUrl = selectAssetUrl(remoteUrl, relativePath);
    }

    // 上传原始图片缩略图
    if (originalThumbExists) {
        const relativePath = buildLocalContentPath(month, barcode, `${barcode}_original_thumb.jpg`);
        const remoteUrl = await uploadFileToR2(
            r2Config,
            paths.originalThumbnailTarget,
            buildR2Key(r2Config, 'content', month, barcode, `${barcode}_original_thumb.jpg`),
            'image/jpeg'
        );
        assetRecord.originalThumbnailUrl = selectAssetUrl(remoteUrl, relativePath);
    }
}

function buildLocalContentPath(month, barcode, ...segments) {
    return path.posix.join('content', month, barcode, ...segments);
}

function buildLocalPublicUrl(relativePath) {
    if (!relativePath) {
        return '';
    }
    return `/${relativePath.replace(/^\/+/, '')}`;
}

function selectAssetUrl(remoteUrl, relativePath) {
    if (remoteUrl) {
        return remoteUrl;
    }
    if (relativePath) {
        return buildLocalPublicUrl(relativePath);
    }
    return '';
}

function buildR2Key(r2Config, ...segments) {
    const cleaned = segments
        .filter(Boolean)
        .map(segment => String(segment).replace(/\\/g, '/').replace(/^\/+|\/+$/g, ''));
    const base = (r2Config?.basePath ?? '').replace(/^\/+|\/+$/g, '');
    if (base) {
        cleaned.unshift(base);
    }
    return cleaned.filter(Boolean).join('/');
}

async function uploadFileToR2(r2Config, filePath, key, contentType) {
    if (!r2Config?.shouldUpload || !r2Config.client || !r2Config.bucket) {
        return null;
    }
    try {
        const fileBuffer = await fs.readFile(filePath);
        await r2Config.client.send(new PutObjectCommand({
            Bucket: r2Config.bucket,
            Key: key,
            Body: fileBuffer,
            ContentType: contentType
        }));
        const publicBase = r2Config.publicUrl?.replace(/\/$/, '');
        if (publicBase) {
            return `${publicBase}/${key}`;
        }
    } catch (error) {
        console.warn(`⚠️  Failed to upload ${key}: ${error.message}`);
    }
    return null;
}

function createR2Config() {
    const shouldUploadEnv = (process.env.UPLOAD_TO_R2 ?? 'true').toLowerCase() !== 'false';
    const endpoint = process.env.R2_ENDPOINT;
    const bucket = process.env.R2_BUCKET_NAME;
    const accessKeyId = process.env.R2_ACCESS_KEY_ID;
    const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
    const basePath = (process.env.R2_BASE_PATH ?? '').replace(/^\/+|\/+$/g, '');
    const publicUrl = (process.env.R2_PUBLIC_URL || process.env.NEXT_PUBLIC_R2_PUBLIC_URL || '').replace(/\/$/, '');

    let client = null;
    let enableUpload = shouldUploadEnv;

    if (enableUpload) {
        if (endpoint && bucket && accessKeyId && secretAccessKey) {
            client = new S3Client({
                region: 'auto',
                endpoint,
                credentials: {
                    accessKeyId,
                    secretAccessKey
                },
                forcePathStyle: true
            });
        } else {
            console.warn('⚠️  R2 配置信息缺失，跳过上传流程');
            enableUpload = false;
        }
    }

    return {
        client,
        bucket,
        basePath,
        publicUrl,
        shouldUpload: enableUpload && !!client
    };
}

async function loadEnvFiles() {
    for (const filename of ENV_FILES) {
        const envPath = path.join(PROJECT_ROOT, filename);
        try {
            const content = await fs.readFile(envPath, 'utf-8');
            applyEnvFile(content);
        } catch {
            // Ignore missing files
        }
    }
}

function applyEnvFile(content) {
    const lines = content.split(/\r?\n/);
    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line || line.startsWith('#')) {
            continue;
        }
        const separatorIndex = line.indexOf('=');
        if (separatorIndex === -1) {
            continue;
        }
        const key = line.slice(0, separatorIndex).trim();
        if (!key || process.env[key]) {
            continue;
        }
        const valueRaw = line.slice(separatorIndex + 1).trim();
        const value = valueRaw.replace(/^['"]|['"]$/g, '');
        process.env[key] = value;
    }
}

// Run the script
main();
