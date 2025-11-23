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

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

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
        // Step 1: Clean target directory
        await cleanTargetDirectory(month);

        // Step 2: Read and filter Excel data
        const books = await readAndFilterExcel(month);
        console.log(`✅ Found ${books.length} books marked as "${PASS_VALUE}"\n`);

        // Step 3: Migrate resources for each book
        await migrateResources(month, books);

        // Step 4: Generate metadata Excel file with filtered data
        await copyMetadata(month, books);

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
async function migrateResources(month, books) {
    const sourceDir = path.join(SOURCES_DIR, month);
    const targetDir = path.join(CONTENT_DIR, month);

    let successCount = 0;
    let errorCount = 0;

    for (const book of books) {
        const barcode = String(book[BARCODE_COLUMN]);
        const bookSourceDir = path.join(sourceDir, barcode);
        const bookTargetDir = path.join(targetDir, barcode);

        try {
            // Check if source directory exists
            try {
                await fs.access(bookSourceDir);
            } catch {
                console.warn(`⚠️  Skipping ${barcode}: Source directory not found`);
                errorCount++;
                continue;
            }

            // Create target directory structure
            await fs.mkdir(bookTargetDir, { recursive: true });
            const picTargetDir = path.join(bookTargetDir, 'pic');
            await fs.mkdir(picTargetDir, { recursive: true });

            // Copy main card image (barcode-S.png -> barcode.png)
            const cardSource = path.join(bookSourceDir, `${barcode}-S.png`);
            const cardTarget = path.join(bookTargetDir, `${barcode}.png`);

            try {
                await fs.copyFile(cardSource, cardTarget);
            } catch {
                console.warn(`⚠️  Warning: Card image not found for ${barcode}`);
            }

            // Copy cover.jpg
            const coverSource = path.join(bookSourceDir, 'pic', 'cover.jpg');
            const coverTarget = path.join(picTargetDir, 'cover.jpg');

            try {
                await fs.copyFile(coverSource, coverTarget);
            } catch {
                console.warn(`⚠️  Warning: Cover image not found for ${barcode}`);
            }

            // Copy qrcode.png
            const qrcodeSource = path.join(bookSourceDir, 'pic', 'qrcode.png');
            const qrcodeTarget = path.join(picTargetDir, 'qrcode.png');

            try {
                await fs.copyFile(qrcodeSource, qrcodeTarget);
            } catch {
                console.warn(`⚠️  Warning: QR code not found for ${barcode}`);
            }

            // Generate thumbnail for the card image (for performance optimization)
            try {
                const thumbnailTarget = path.join(bookTargetDir, `${barcode}_thumb.jpg`);
                await sharp(cardSource)
                    .resize(400, null, { withoutEnlargement: true })
                    .jpeg({ quality: 85 })
                    .toFile(thumbnailTarget);
            } catch (error) {
                // Thumbnail generation is optional, don't fail the whole process
                console.warn(`⚠️  Warning: Could not generate card thumbnail for ${barcode}`);
            }

            // Generate thumbnail for the cover image (used on the canvas cards)
            try {
                const coverThumbnailTarget = path.join(picTargetDir, 'cover_thumb.jpg');
                await sharp(coverSource)
                    .resize(400, null, { withoutEnlargement: true })
                    .jpeg({ quality: 85 })
                    .toFile(coverThumbnailTarget);
            } catch (error) {
                console.warn(`⚠️  Warning: Could not generate cover thumbnail for ${barcode}`);
            }

            successCount++;
            console.log(`✅ Processed: ${barcode}`);
        } catch (error) {
            console.error(`❌ Error processing ${barcode}:`, error.message);
            errorCount++;
        }
    }

    console.log(`\n📊 Migration Summary:`);
    console.log(`   ✅ Success: ${successCount}`);
    console.log(`   ❌ Errors: ${errorCount}`);
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
async function copyMetadata(month, books) {
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

// Run the script
main();
