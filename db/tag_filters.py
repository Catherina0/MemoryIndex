#region 标签展示过滤

"""
集中管理需要从数据库统计和展示层隐藏的噪声标签。
"""

from typing import Iterable, List, Optional, Tuple


HIDDEN_TAG_NAMES: Tuple[str, ...] = (
    "标签",
    "---",
    "详细内容概括",
    "详细内容概括完整版",
    "OCR",
)

_HIDDEN_TAG_KEYS = {name.casefold() for name in HIDDEN_TAG_NAMES}


def normalize_tag_name(tag_name: Optional[str]) -> str:
    """标准化标签名，统一去掉首尾空白。"""
    return (tag_name or "").strip()


def is_hidden_tag(tag_name: Optional[str]) -> bool:
    """判断标签是否属于应隐藏的噪声标签。"""
    normalized = normalize_tag_name(tag_name)
    return bool(normalized) and normalized.casefold() in _HIDDEN_TAG_KEYS


def filter_display_tags(tag_names: Iterable[str]) -> List[str]:
    """过滤噪声标签，并按大小写不敏感规则去重。"""
    visible_tags: List[str] = []
    seen = set()

    for tag_name in tag_names:
        normalized = normalize_tag_name(tag_name)
        if not normalized or is_hidden_tag(normalized):
            continue

        tag_key = normalized.casefold()
        if tag_key in seen:
            continue

        seen.add(tag_key)
        visible_tags.append(normalized)

    return visible_tags


def split_display_tags(tag_string: Optional[str]) -> List[str]:
    """将数据库中的聚合标签字符串拆分并过滤。"""
    if not tag_string:
        return []

    return filter_display_tags(tag_string.split(", "))


def get_hidden_tag_sql(column_name: str = "name") -> Tuple[str, List[str]]:
    """返回可复用的 SQL 过滤条件和参数。"""
    placeholders = ", ".join("?" for _ in HIDDEN_TAG_NAMES)
    clause = f"LOWER(TRIM({column_name})) NOT IN ({placeholders})"
    params = [name.casefold() for name in HIDDEN_TAG_NAMES]
    return clause, params


#endregion
