import React from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface InkPanelProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'dark' | 'glass';
}

export const InkPanel: React.FC<InkPanelProps> = ({
  children,
  className = '',
  variant = 'default',
  ...props
}) => {
  const baseStyles = "relative overflow-hidden rounded-lg border backdrop-blur-md transition-all";
  
  const variants = {
    default: "bg-[#F5F5F0]/90 border-[#1a1a1a]/10 text-[#1a1a1a] shadow-lg",
    dark: "bg-[#1a1a1a]/90 border-white/10 text-[#F5F5F0] shadow-xl",
    glass: "bg-white/10 border-white/20 text-white shadow-lg backdrop-blur-xl"
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 10, scale: 0.95 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {/* Paper Texture Overlay */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};
