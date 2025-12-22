import { z } from 'zod';

/**
 * 数据规范化器 - 将原始JSON数据转换为标准格式
 * 负责坐标、年份、馆藏元数据等细粒度规范化
 */

// 基础坐标验证
export const CoordinateSchema = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180)
});

// 地理信息验证
export const LocationSchema = z.object({
  name: z.string(),
  coordinates: CoordinateSchema,
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]).optional()
});

// 作品路线验证
export const RouteSchema = z.object({
  id: z.string(),
  start_location: LocationSchema,
  end_location: LocationSchema,
  year: z.number().min(1400).max(new Date().getFullYear()).optional(),
  description: z.string().optional(),
  collection_info: z.object({
    has_collection: z.boolean(),
    collection_meta: z.union([
      z.object({
        title: z.string(),
        date: z.string(),
        location: z.string()
      }),
      z.object({}).passthrough() // 允许空对象
    ]).optional()
  }).default({ has_collection: false })
});

// 作者作品验证
export const WorkSchema = z.object({
  id: z.string(),
  title: z.string(),
  year: z.number().min(1400).max(new Date().getFullYear()).optional(),
  routes: z.array(RouteSchema),
  metadata: z.object({
    genre: z.string(),
    themes: z.array(z.string()),
    language: z.string()
  })
});

// 作者验证
export const AuthorSchema = z.object({
  id: z.string(),
  name: z.string(),
  birth_year: z.number().min(1400).max(new Date().getFullYear()).optional(),
  death_year: z.number().min(1400).max(new Date().getFullYear()).optional(),
  biography: z.string(),
  works: z.array(WorkSchema)
});

// 导出类型定义
export type Coordinate = z.infer<typeof CoordinateSchema>;
export type Location = z.infer<typeof LocationSchema>;
export type Route = z.infer<typeof RouteSchema>;
export type Work = z.infer<typeof WorkSchema>;
export type Author = z.infer<typeof AuthorSchema>;

/**
 * 规范化坐标数据
 * @param coords 原始坐标数据
 * @returns 规范化的坐标对象
 */
export function normalizeCoordinate(coords: unknown): Coordinate {
  try {
    return CoordinateSchema.parse(coords);
  } catch (error) {
    console.error('坐标数据规范化失败:', error);
    throw new Error(`无效的坐标数据: ${JSON.stringify(coords)}`);
  }
}

/**
 * 规范化地理信息
 * @param location 原始地理信息
 * @returns 规范化的地理信息对象
 */
export function normalizeLocation(location: unknown): Location {
  try {
    const normalized = LocationSchema.parse(location);
    
    // 如果没有提供边界框，基于坐标计算
    if (!normalized.bbox) {
      const { lat, lng } = normalized.coordinates;
      const delta = 0.01; // 10km 左右的范围
      normalized.bbox = [
        lng - delta, // west
        lat - delta, // south  
        lng + delta, // east
        lat + delta  // north
      ];
    }
    
    return normalized;
  } catch (error) {
    console.error('地理信息规范化失败:', error);
    throw new Error(`无效的地理信息: ${JSON.stringify(location)}`);
  }
}

/**
 * 规范化作品路线
 * @param route 原始路线数据
 * @returns 规范化的路线对象
 */
export function normalizeRoute(route: unknown): Route {
  try {
    const normalized = RouteSchema.parse(route);
    
    // 规范化起点和终点地理信息
    normalized.start_location = normalizeLocation((route as { start_location: unknown }).start_location);
    normalized.end_location = normalizeLocation((route as { end_location: unknown }).end_location);
    
    // 年份回退策略：如果路线年份缺失，使用作品年份
    if (!normalized.year && (route as { work_year?: number }).work_year) {
      normalized.year = (route as { work_year: number }).work_year;
    }
    
    return normalized;
  } catch (error) {
    console.error('路线规范化失败:', error);
    throw new Error(`无效的路线数据: ${JSON.stringify(route)}`);
  }
}

/**
 * 规范化作者作品
 * @param work 原始作品数据
 * @returns 规范化的作品对象
 */
export function normalizeWork(work: unknown): Work {
  try {
    const normalized = WorkSchema.parse(work);
    
    // 规范化所有路线
    normalized.routes = (work as { routes: unknown[] }).routes.map((route: unknown) => normalizeRoute(route));
    
    return normalized;
  } catch (error) {
    console.error('作品规范化失败:', error);
    throw new Error(`无效的作品数据: ${JSON.stringify(work)}`);
  }
}

/**
 * 规范化作者数据
 * @param author 原始作者数据
 * @returns 规范化的作者对象
 */
export function normalizeAuthor(author: unknown): Author {
  try {
    const normalized = AuthorSchema.parse(author);
    
    // 规范化所有作品
    normalized.works = (author as { works: unknown[] }).works.map((work: unknown) => normalizeWork(work));
    
    return normalized;
  } catch (error) {
    console.error('作者数据规范化失败:', error);
    throw new Error(`无效的作者数据: ${JSON.stringify(author)}`);
  }
}