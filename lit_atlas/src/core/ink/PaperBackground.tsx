import React from 'react';

export const PaperBackground: React.FC = () => {
    return (
        <div className="fixed inset-0 pointer-events-none z-0">
            {/* Base Paper Color */}
            <div className="absolute inset-0 bg-[#F5F5F0]" />

            {/* Noise Texture */}
            <div
                className="absolute inset-0 opacity-[0.05]"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                }}
            />

            {/* Vignette */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.1)_100%)]" />
        </div>
    );
};
