/** @type {import('jest').Config} */
const config = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^d3$': '<rootDir>/tests/__mocks__/d3.ts',
    '^d3-geo$': '<rootDir>/tests/__mocks__/d3.ts',
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setupTests.ts'],
  testPathIgnorePatterns: ['<rootDir>/.next/', '<rootDir>/node_modules/'],
  collectCoverageFrom: ['src/**/*.{ts,tsx}', '!src/**/*.d.ts'],
  transform: {
    '^.+\\.(ts|tsx)$': [
      'ts-jest',
      {
        tsconfig: '<rootDir>/tsconfig.test.json'
      }
    ]
  },
};

export default config;
