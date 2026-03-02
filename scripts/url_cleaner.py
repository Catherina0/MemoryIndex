#!/usr/bin/env python3
"""
URL 反追踪 & 短链接还原工具
参考: UrlCleaner_new.html
用法: python scripts/url_cleaner.py <url_or_text>
"""

import re
import sys
import urllib.parse
import urllib.request

# 长链接域名白名单 - 这些域名即使路径短也不进行短链接展开
LONG_LINK_WHITELIST = [
    'zhihu.com', 'www.zhihu.com',
]

# 已知的短链接域名
SHORT_LINK_DOMAINS = [
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly', 'buff.ly',
    'short.link', 'is.gd', 'v.ht', 'tb.cn', '3.cn', 'xhslink.com',
    'dwz.cn', 'suo.im', 'mrw.so', 'url.cn', 'sina.lt', 'qq.cn',
    'u.to', 'tiny.cc', 'rebrand.ly', 'cutt.ly', 'short.io',
    'b23.tv',       # B站短链接
    'j.cn',         # 京东短链接
    'c.tb.cn',      # 淘宝短链接
]

# 追踪参数列表
TRACKER_PARAMS = [
    # 通用追踪参数
    'ref', 'referrer', 'gclid', 'fbclid', 'dclid', 'msclkid', 'icid',
    'mcid', 'gbraid', 'wbraid', 's_kwcid', 'utm_psn', 'campaign', 'utm_source',
    'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id',
    'utm_nooverride', 'utm_expid', 'utm_referrer', 'uct2',
    # 淘宝/天猫
    '-Arouter', 'buvid', 'from_spmid', 'is_story_h5', 'mid', 'p', 'plat_id',
    'share_from', 'share_medium', 'share_plat', 'share_session_id',
    'share_source', 'share_tag', 'spmid', 'timestamp', 'unique_k', 'up_id',
    'app_version', 'dlt', 'channelId', 'ADTAG', 'openinqqmusic', 'songtype', 'source',
    'vd_source', 'ut_sk', 'sourceType', 'suid', 'shareUniqueId', 'un', 'share_crt_v',
    'spm', 'wxsign', 'tbSocialPopKey', 'short_name', 'sp_tk', 'bxsign',
    # 网易云音乐
    'fx-wechatnew', 'fx-wxqd', 'fx-wordtest', 'fx-listentest', 'H5_DownloadVIPGift',
    'playerUIModeId', 'PlayerStyles_SynchronousSharing', 'sc', 'tn',
    # 小红书
    'app_platform', 'share_from_user_hidden', 'type',
    'author_share', 'xhsshare', 'shareRedId', 'apptime', 'share_id', 'xsec_source', 'xsec_token',
    # 京东
    'gx', 'gxd', 'ad_od', 'appid', 'evtype', 'evurl', 'rpid',
    # 抖音
    'previous_page', 'enter_method', 'enter_from', 'is_copy_url', 'checksum',
    # 知乎
    'utm_oi', 'utm_lens', 'share_code',
    # 微信
    'from', 'isappinstalled', 'scene', 'subscene', 'sessionid', 'clicktime', 'enterid',
    # B站
    'bbid', 'ts',
    # 通用社交媒体
    'igshid', 'story_media_id', '_r', 'hl', '_nc_ht', '_nc_cat', '_nc_ohc', 'oh', 'oe', 'userid'
]


def extract_url(text: str) -> str | None:
    """从文本中提取第一个 URL"""
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(1) if match else None


def should_expand_as_short_link(url: str) -> bool:
    """判断是否应进行短链接展开"""
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ''

        # 白名单域名直接跳过展开
        for domain in LONG_LINK_WHITELIST:
            if hostname == domain or hostname.endswith('.' + domain):
                return False

        # 已知短链接域名必须展开
        for domain in SHORT_LINK_DOMAINS:
            if hostname == domain or hostname.endswith('.' + domain):
                return True

        # 路径较短的未知域名视为短链接
        path = parsed.path
        if path and len(path) <= 15 and re.match(r'^/[a-zA-Z0-9_-]+/?$', path):
            return True

        return False
    except Exception:
        return False


def resolve_short_url(url: str) -> str:
    """跟踪 HTTP 重定向，还原真实 URL"""
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; URLCleaner/1.0)'}
        )
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        response = opener.open(req, timeout=10)
        return response.url
    except Exception as e:
        print(f"⚠️  短链接展开失败: {e}", file=sys.stderr)
        return url


def remove_trackers(url: str) -> str:
    """去除 URL 中的追踪参数，并处理平台特殊规则"""
    try:
        # 处理京东重定向
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        hostname = parsed.hostname.lower() if parsed.hostname else ''

        # 京东重定向
        if 'jd.com' in hostname and 'returnurl' in params:
            return urllib.parse.unquote(params['returnurl'][0])

        # 淘宝商品特殊处理
        if hostname == 'item.taobao.com' and parsed.path == '/item.htm':
            if 'id' in params:
                return f"https://item.taobao.com/item.htm?id={params['id'][0]}"

        # 京东商品特殊处理
        if 'jd.com' in hostname:
            m = re.search(r'/(product|item)/(\d+)\.html', parsed.path)
            if m:
                return f"https://item.jd.com/product/{m.group(2)}.html"

        # 小红书特殊处理：只删特定参数
        if 'xiaohongshu.com' in hostname:
            xhs_params = [
                'app_platform', 'app_version', 'share_from_user_hidden', 'type',
                'author_share', 'xhsshare', 'shareRedId', 'apptime', 'share_id',
                'xsec_source', 'xsec_token'
            ]
            new_params = {k: v for k, v in params.items() if k not in xhs_params}
            new_query = urllib.parse.urlencode(new_params, doseq=True)
            return urllib.parse.urlunparse(parsed._replace(query=new_query))

        # 抖音特殊处理
        if 'douyin.com' in hostname:
            m = re.search(r'/video/(\d+)', parsed.path)
            if m:
                return f"https://www.douyin.com/video/{m.group(1)}"

        # 网易云音乐特殊处理
        if 'music.163.com' in hostname and '/song' in parsed.path:
            if 'id' in params:
                return f"https://y.music.163.com/m/song?id={params['id'][0]}"

        # 通用：删除所有已知追踪参数
        new_params = {k: v for k, v in params.items() if k not in TRACKER_PARAMS}
        new_query = urllib.parse.urlencode(new_params, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    except Exception as e:
        print(f"⚠️  URL 处理失败: {e}", file=sys.stderr)
        return url


def clean_url(raw: str) -> dict:
    """主入口：接收文本，返回 {original, expanded, cleaned} 字典"""
    url = extract_url(raw)
    if not url:
        return {'error': '未在输入中检测到有效 URL'}

    expanded = url
    if should_expand_as_short_link(url):
        expanded = resolve_short_url(url)

    cleaned = remove_trackers(expanded)
    return {
        'original': url,
        'expanded': expanded,
        'cleaned': cleaned,
        'changed': cleaned != url
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/url_cleaner.py <URL或包含URL的文本>")
        print("      python scripts/url_cleaner.py --clean-only <URL或文本>  # 仅输出清理后链接")
        sys.exit(1)

    # --clean-only 模式：仅输出清理后的 URL（适合管道 | pbcopy）
    clean_only = '--clean-only' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--clean-only']
    raw = " ".join(args)

    result = clean_url(raw)

    if 'error' in result:
        if not clean_only:
            print(f"❌ {result['error']}")
        sys.exit(1)

    if clean_only:
        print(result['cleaned'])
        return

    print(f"🔗 原始链接:   {result['original']}")
    if result['expanded'] != result['original']:
        print(f"🔄 还原链接:   {result['expanded']}")
    print(f"✅ 清理后链接:")
    print(f"   {result['cleaned']}")


if __name__ == '__main__':
    main()
