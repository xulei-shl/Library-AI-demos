## 豆瓣图书

```
curl --request GET \
  --url https://m.douban.com/rexxar/api/v2/subject/37351901 \
  --header 'Accept: application/json, text/plain, */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \
  --header 'Connection: keep-alive' \
  --header 'Referer: https://m.douban.com/' \
  --header 'Sec-Fetch-Dest: empty' \
  --header 'Sec-Fetch-Mode: cors' \
  --header 'Sec-Fetch-Site: same-origin' \
  --header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
```

## 豆瓣电影

```
curl --request GET \
  --url 'https://m.douban.com/rexxar/api/v2/subject/recent_hot/movie?start=0&limit=20' \
  --header 'Accept: application/json, text/plain, */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8' \
  --header 'Connection: keep-alive' \
  --header 'Referer: https://m.douban.com/' \
  --header 'Sec-Fetch-Dest: empty' \
  --header 'Sec-Fetch-Mode: cors' \
  --header 'Sec-Fetch-Site: same-origin' \
  --header 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
```

---

## 致谢

[x1ao4/douban-api: 豆瓣 API 服务 - 基于豆瓣移动端 API 获取影视热门榜单数据](https://github.com/x1ao4/douban-api)