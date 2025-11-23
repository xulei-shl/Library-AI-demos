/**
 * Simple seeded random number generator
 * Returns a deterministic random number between 0 and 1 based on a seed string
 */
export function seededRandom(seed: string): number {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        const char = seed.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
    }

    // Use a simple LCG (Linear Congruential Generator)
    const x = Math.sin(hash) * 10000;
    return x - Math.floor(x);
}

/**
 * Generate multiple seeded random numbers from a single seed
 */
export function seededRandoms(seed: string, count: number): number[] {
    const results: number[] = [];
    for (let i = 0; i < count; i++) {
        results.push(seededRandom(`${seed}-${i}`));
    }
    return results;
}
