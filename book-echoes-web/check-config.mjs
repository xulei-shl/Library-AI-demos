import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 读取 .env 文件
const envPath = join(__dirname, '.env');
const envContent = readFileSync(envPath, 'utf-8');

console.log('=== .env 文件内容 ===');
console.log(envContent);
console.log('\n');

// 解析环境变量
const envVars = {};
envContent.split('\n').forEach(line => {
  const trimmed = line.trim();
  if (trimmed && !trimmed.startsWith('#')) {
    const [key, ...valueParts] = trimmed.split('=');
    if (key && valueParts.length > 0) {
      envVars[key] = valueParts.join('=');
    }
  }
});

console.log('=== 解析后的环境变量 ===');
console.log(JSON.stringify(envVars, null, 2));
console.log('\n');

// 检查关键的环境变量
const r2PublicUrl = envVars.NEXT_PUBLIC_R2_PUBLIC_URL || envVars.R2_PUBLIC_URL;
console.log('=== R2 公共URL ===');
console.log('NEXT_PUBLIC_R2_PUBLIC_URL:', envVars.NEXT_PUBLIC_R2_PUBLIC_URL);
console.log('R2_PUBLIC_URL:', envVars.R2_PUBLIC_URL);
console.log('使用的URL:', r2PublicUrl);
console.log('\n');

// 模拟 next.config.ts 的逻辑
if (r2PublicUrl) {
  try {
    const url = new URL(r2PublicUrl);
    console.log('=== URL 解析结果 ===');
    console.log('Protocol:', url.protocol);
    console.log('Hostname:', url.hostname);
    console.log('Pathname:', url.pathname);
    console.log('\n');

    console.log('=== 生成的 remotePatterns 配置 ===');
    const pattern = {
      protocol: url.protocol.replace(':', ''),
      hostname: url.hostname,
      pathname: '/**'
    };
    console.log(JSON.stringify(pattern, null, 2));
  } catch (error) {
    console.error('URL 解析失败:', error.message);
  }
} else {
  console.log('警告: 未找到 R2_PUBLIC_URL 环境变量');
}
