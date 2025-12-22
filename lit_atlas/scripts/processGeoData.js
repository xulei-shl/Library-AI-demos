#!/usr/bin/env node
/**
 * 地理数据处理脚本
 * 功能：裁剪 GeoJSON 字段，减少文件体积
 * 参考：@docs/design/geodata_specification_20251222.md
 */

const fs = require('fs');
const path = require('path');

const INPUT = 'raw/ne_50m_admin_0_countries.geojson';
const OUTPUT = 'public/data/geo/world.json';

console.log('🌍 开始处理 GeoJSON 数据...');

// 检查输入文件
if (!fs.existsSync(INPUT)) {
  console.error(`❌ 错误：找不到输入文件 ${INPUT}`);
  console.log('📥 请先下载 Natural Earth 数据：');
  console.log('   https://www.naturalearthdata.com/downloads/50m-cultural-vectors/');
  console.log('   并解压到 raw/ 目录');
  process.exit(1);
}

// 读取并解析
const data = JSON.parse(fs.readFileSync(INPUT, 'utf8'));

// 裁剪字段（仅保留必要属性）
data.features = data.features.map((f) => ({
  type: f.type,
  geometry: f.geometry,
  properties: {
    name: f.properties.NAME,
    iso: f.properties.ISO_A3,
  },
}));

// 确保输出目录存在
fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });

// 写入输出
fs.writeFileSync(OUTPUT, JSON.stringify(data));

console.log(`✅ 处理完成！`);
console.log(`   输出路径: ${OUTPUT}`);
console.log(`   国家数量: ${data.features.length}`);
console.log(`   文件大小: ${(fs.statSync(OUTPUT).size / 1024).toFixed(2)} KB`);
console.log('');
console.log('💡 提示：如需进一步简化，请运行：');
console.log('   npx mapshaper world.json -simplify 0.5% -o world-simplified.json');
