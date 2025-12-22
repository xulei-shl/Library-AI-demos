/**
 * 性能基准测试脚本
 * 参考：@docs/design/performance_budget_20251222.md
 * 
 * 使用方法：
 * 1. 启动开发服务器：npm run dev
 * 2. 运行测试：node scripts/performanceBenchmark.js
 */

const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'http://localhost:3000';
const OUTPUT_DIR = path.join(__dirname, '../runtime/performance');

// 性能预算
const PERFORMANCE_BUDGET = {
  FCP: 1500, // First Contentful Paint
  LCP: 2500, // Largest Contentful Paint
  TTI: 3000, // Time to Interactive
  FID: 100,  // First Input Delay
  CLS: 0.1,  // Cumulative Layout Shift
};

async function runLighthouse() {
  console.log('🚀 Starting Lighthouse audit...');
  
  // 启动 Chrome
  const chrome = await chromeLauncher.launch({
    chromeFlags: ['--headless', '--disable-gpu'],
  });

  const options = {
    logLevel: 'info',
    output: 'json',
    onlyCategories: ['performance'],
    port: chrome.port,
  };

  try {
    // 运行 Lighthouse
    const runnerResult = await lighthouse(TARGET_URL, options);
    
    // 提取指标
    const { lhr } = runnerResult;
    const metrics = {
      FCP: lhr.audits['first-contentful-paint'].numericValue,
      LCP: lhr.audits['largest-contentful-paint'].numericValue,
      TTI: lhr.audits['interactive'].numericValue,
      CLS: lhr.audits['cumulative-layout-shift'].numericValue,
      performanceScore: lhr.categories.performance.score * 100,
    };

    // 检查是否满足预算
    const results = {
      timestamp: new Date().toISOString(),
      url: TARGET_URL,
      metrics,
      budget: PERFORMANCE_BUDGET,
      passed: true,
      violations: [],
    };

    // 验证每个指标
    if (metrics.FCP > PERFORMANCE_BUDGET.FCP) {
      results.passed = false;
      results.violations.push(`FCP: ${metrics.FCP}ms > ${PERFORMANCE_BUDGET.FCP}ms`);
    }
    if (metrics.LCP > PERFORMANCE_BUDGET.LCP) {
      results.passed = false;
      results.violations.push(`LCP: ${metrics.LCP}ms > ${PERFORMANCE_BUDGET.LCP}ms`);
    }
    if (metrics.TTI > PERFORMANCE_BUDGET.TTI) {
      results.passed = false;
      results.violations.push(`TTI: ${metrics.TTI}ms > ${PERFORMANCE_BUDGET.TTI}ms`);
    }
    if (metrics.CLS > PERFORMANCE_BUDGET.CLS) {
      results.passed = false;
      results.violations.push(`CLS: ${metrics.CLS} > ${PERFORMANCE_BUDGET.CLS}`);
    }

    // 保存结果
    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    const filename = `benchmark_${Date.now()}.json`;
    const filepath = path.join(OUTPUT_DIR, filename);
    fs.writeFileSync(filepath, JSON.stringify(results, null, 2));

    // 输出结果
    console.log('\n📊 Performance Metrics:');
    console.log(`  FCP: ${metrics.FCP.toFixed(0)}ms (budget: ${PERFORMANCE_BUDGET.FCP}ms)`);
    console.log(`  LCP: ${metrics.LCP.toFixed(0)}ms (budget: ${PERFORMANCE_BUDGET.LCP}ms)`);
    console.log(`  TTI: ${metrics.TTI.toFixed(0)}ms (budget: ${PERFORMANCE_BUDGET.TTI}ms)`);
    console.log(`  CLS: ${metrics.CLS.toFixed(3)} (budget: ${PERFORMANCE_BUDGET.CLS})`);
    console.log(`  Performance Score: ${metrics.performanceScore.toFixed(0)}/100`);

    if (results.passed) {
      console.log('\n✅ All performance budgets met!');
    } else {
      console.log('\n❌ Performance budget violations:');
      results.violations.forEach((v) => console.log(`  - ${v}`));
    }

    console.log(`\n📁 Results saved to: ${filepath}`);

    return results;
  } finally {
    await chrome.kill();
  }
}

// 运行测试
runLighthouse()
  .then((results) => {
    process.exit(results.passed ? 0 : 1);
  })
  .catch((error) => {
    console.error('❌ Benchmark failed:', error);
    process.exit(1);
  });
