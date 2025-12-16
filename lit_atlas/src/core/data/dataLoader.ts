import { Author } from './normalizers';
import { normalizeAuthor, AuthorSchema } from './normalizers';

/**
 * 数据加载器 - 读取并解析作者JSON
 * 完成字段校验、默认值补齐和缓存管理
 */

// 缓存管理
const dataCache = new Map<string, Author>();

// 加载状态
const loadingStates = new Map<string, Promise<Author>>();

/**
 * 错误类型定义
 */
export class DataLoadError extends Error {
  constructor(
    message: string,
    public authorId: string,
    public cause?: unknown
  ) {
    super(message);
    this.name = 'DataLoadError';
  }
}

/**
 * 作者数据载荷
 */
export interface AuthorPayload {
  author: Author;
  loadedAt: Date;
  version: string;
}

/**
 * 从文件系统加载作者数据
 * @param authorId 作者ID
 * @returns 规范化后的作者数据
 */
export async function loadAuthor(authorId: string): Promise<Author> {
  // 检查缓存
  if (dataCache.has(authorId)) {
    console.info(`使用缓存加载作者: ${authorId}`);
    return dataCache.get(authorId)!;
  }

  // 检查是否正在加载
  if (loadingStates.has(authorId)) {
    console.info(`等待正在进行的加载请求: ${authorId}`);
    return loadingStates.get(authorId)!;
  }

  // 开始新的加载请求
  const loadPromise = performLoad(authorId);
  loadingStates.set(authorId, loadPromise);

  try {
    const author = await loadPromise;
    
    // 缓存结果
    dataCache.set(authorId, author);
    
    // 清理加载状态
    loadingStates.delete(authorId);
    
    console.info(`成功加载作者数据: ${authorId}`, {
      name: author.name,
      worksCount: author.works.length,
      totalRoutes: author.works.reduce((sum, work) => sum + work.routes.length, 0)
    });

    return author;
  } catch (error) {
    // 清理加载状态
    loadingStates.delete(authorId);
    
    console.error(`加载作者数据失败: ${authorId}`, error);
    throw new DataLoadError(
      `无法加载作者 "${authorId}" 的数据`,
      authorId,
      error
    );
  }
}

/**
 * 执行实际的加载逻辑
 * @param authorId 作者ID
 * @returns 规范化后的作者数据
 */
async function performLoad(authorId: string): Promise<Author> {
  try {
    // 构建文件路径
    const filePath = `/data/authors/${authorId}.json`;
    
    console.info(`开始加载作者数据: ${filePath}`);
    
    // 获取JSON数据
    const response = await fetch(filePath);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const rawData = await response.json();
    
    // 验证JSON结构
    if (!rawData || typeof rawData !== 'object') {
      throw new Error('无效的JSON格式');
    }
    
    // 使用Zod验证数据结构
    const validationResult = AuthorSchema.safeParse(rawData);
    
    if (!validationResult.success) {
      console.error('数据验证失败:', validationResult.error);
      throw new Error(`数据验证失败: ${validationResult.error.message}`);
    }
    
    // 规范化数据
    const normalizedAuthor = normalizeAuthor(rawData);
    
    // 额外的业务逻辑验证
    validateBusinessRules(normalizedAuthor);
    
    return normalizedAuthor;
    
  } catch (error) {
    if (error instanceof DataLoadError) {
      throw error;
    }
    
    // 处理网络或解析错误
    throw new DataLoadError(
      `加载作者 "${authorId}" 时发生未知错误`,
      authorId,
      error
    );
  }
}

/**
 * 业务规则验证
 * @param author 作者数据
 */
function validateBusinessRules(author: Author): void {
  // 检查是否有作品
  if (!author.works || author.works.length === 0) {
    throw new Error(`作者 "${author.name}" 没有作品数据`);
  }
  
  // 检查每部作品的路线
  author.works.forEach(work => {
    if (!work.routes || work.routes.length === 0) {
      console.warn(`作品 "${work.title}" 没有路线数据`);
    }
    
    // 检查路线坐标有效性
    work.routes.forEach(route => {
      if (!route.start_location || !route.end_location) {
        throw new Error(`路线 "${route.id}" 缺少地理信息`);
      }
    });
  });
}

/**
 * 获取所有已缓存的作者ID
 * @returns 已缓存的作者ID列表
 */
export function getCachedAuthorIds(): string[] {
  return Array.from(dataCache.keys());
}

/**
 * 清除指定作者的缓存
 * @param authorId 作者ID，为空则清除所有缓存
 */
export function clearCache(authorId?: string): void {
  if (authorId) {
    dataCache.delete(authorId);
    console.info(`清除作者缓存: ${authorId}`);
  } else {
    dataCache.clear();
    console.info('清除所有作者缓存');
  }
}

/**
 * 获取缓存统计信息
 * @returns 缓存统计
 */
export function getCacheStats() {
  return {
    cachedAuthors: dataCache.size,
    loadingAuthors: loadingStates.size,
    authorIds: Array.from(dataCache.keys())
  };
}

/**
 * 预加载多个作者数据
 * @param authorIds 作者ID列表
 * @returns Promise数组
 */
export function preloadAuthors(authorIds: string[]): Promise<Author>[] {
  return authorIds.map(id => loadAuthor(id));
}