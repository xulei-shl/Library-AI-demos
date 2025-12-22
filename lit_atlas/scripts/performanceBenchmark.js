#!/usr/bin/env node
/**
 * 性能基准测试脚本
 * 参考：@docs/design/performance_budget_20251222.md
 * 
 * 运行方式：
 * - 开发环境：node scripts/performanceBenchmark.js
 * - CI 环境：npm run test:performance
 */

const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const fs = require('fs');
const path = require('path');

// 性能预算阈值
const PERFORMANCE_BUDGET = {
  FCP: 1500, // 首屏渲染 < 1.5s
  TTI: 3000, // 可交互时间 < 3.0s
  LCP: 2500, // 最大内容绘制 < 2.5s
  FID: 100, // 首次输入延迟 < 100ms
  CLS: 0.1, // 累积布局偏移 < 0.1
};

async function runLighthouse(url) {
  console.log('🚀 启动 Chrome...');
  const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless'] });

  console.log(`📊 运行 Lighthouse 测试: ${url}`);
  const options = {
    logLevel: 'info',
    output: 'json',
    onlyCategories: ['performance'],
    port: chrome.port,
  };

  const runnerResult = await lighthouse(url, options);

  await chrome.kill();

  return runnerResult.lhr;
}

function analyzeResults(lhr) {
  const metrics = {
    FCP: lhr.audits['first-contentful-paint'].numericValue,
    TTI: lhr.audits['interactive'].numericValue,
    LCP: lhr.audits['largest-contentful-paint'].numericValue,
    CLS: lhr.audits['cumulative-layout-shift'].numericValue,
    performanceScore: lhr.categories.performance.score * 100,
  };

  console.log('\n📈 性能指标：');
  console.log('─'.repeat(50));

  const results = [];
  for (const [key, value] of Object.entries(metrics)) {
    if (key === 'performanceScore') {
      console.log(`${key}: ${value.toFixed(0)}/100`);
      continue;
    }

    const budget = PERFORMANCE_BUDGET[key];
    const passed = value <= budget;
    const status = passed ? '✅' : '❌';

    console.log(`${status} ${key}: ${value.toFixed(0)}ms (预算: ${budget}ms)`);
    results.push({ metric: key, value, budget, passed });
  }

  console.log('─'.repeat(50));

  return { metrics, results };
}

function saveResults(data) {
  const outputDir = 'runtime/outputs/performance';
  fs.mkdirSync(outputDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `benchmark_${timestamp}.json`;
  const filepath = path.join(outputDir, filename);

  fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
  console.log(`\n💾 结果已保存: ${filepath}`);

  // 保存最新结果为 latest.json
  const latestPath = path.join(outputDir, 'latest.json');
  fs.writeFileSync(latestPath, JSON.stringify(data, null, 2));
}

async function main() {
  const url = process.env.TEST_URL || 'http://localhost:3000';

  console.log('🎯 墨迹与边界 - 性能基准测试');
  console.log(`   目标 URL: ${url}`);
  console.log('');

  try {
    const lhr = await runLighthouse(url);
    const { metrics, results } = analyzeResults(lhr);

    const allPassed = results.every((r) => r.passed);
    const data = {
      timestamp: new Date().toISOString(),
      url,
      metrics,
      results,
      passed: allPassed,
    };

    saveResults(data);

    if (!allPassed) {
      console.log('\n⚠️  部分指标未达标，请优化性能！');
      process.exit(1);
    } else {
      console.log('\n🎉 所有性能指标达标！');
    }
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    console.log('\n💡 提示：请确保开发服务器正在运行（npm run dev）');
    process.exit(1);
  }
}

// 仅在直接运行时执行（非 require 导入）
if (require.main === module) {
  main();
}

module.exports = { runLighthouse, analyzeResults };
