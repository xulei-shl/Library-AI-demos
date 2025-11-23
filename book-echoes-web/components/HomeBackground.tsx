'use client';

import { motion } from 'framer-motion';

type HomeBackgroundProps = {
  projectName: string;
  institutionName: string;
};

export default function HomeBackground({
  projectName,
  institutionName
}: HomeBackgroundProps) {
  return (
    <div className="home-bg" aria-hidden="true">
      {/* 主背景渐变 - 柔和的放射渐变 */}
      <div className="home-bg__gradient" />

      {/* 微妙网格 */}
      <div className="home-bg__grid" />

      {/* 光晕效果 */}
      <div className="home-bg__radial home-bg__radial--hero" />
      <div className="home-bg__radial home-bg__radial--secondary" />

      {/* 装饰性排版 - 优雅的文字水印 (移至右下角) */}
      <motion.div
        className="home-bg__watermark"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.2, delay: 0.3 }}
      >
        <div className="home-bg__watermark-main">
          {projectName.split('').map((char, i) => (
            <motion.span
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + i * 0.1, duration: 0.8 }}
            >
              {char}
            </motion.span>
          ))}
        </div>
        <motion.div
          className="home-bg__watermark-sub"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 1.2, duration: 1 }}
        >
          {institutionName}
        </motion.div>
      </motion.div>
    </div>
  );
}
