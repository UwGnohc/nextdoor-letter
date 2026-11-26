"""Translate a single selected, server-resolved public headline using MyMemory's documented GET API."""

from html import unescape
from http.client import HTTPException
import json
import re
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from community_titles import chinese_title


API = "https://api.mymemory.translated.net/get"
HAN = re.compile(r"[\u3400-\u9fff]")
KANA = re.compile(r"[ぁ-ヺ]")
HANGUL = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣ]")
MARKUP = re.compile(r"</?[a-zA-Z][\w:-]*(?:\s[^<>]*?)?\s*/?>|<!--")
LINK_OR_HANDLE = re.compile(
    r"(?:[a-z][a-z0-9+.\-]*://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.\w+|(?<!\w)@[\w.-]+(?:@[\w.-]+)?"
    r"|\b(?:[a-z0-9-]+\.)+[a-z]{2,24}(?:/\S*)?\b",
    re.I,
)
WORDS = {
    "en": "i you this that the what where which who would is are was were how did does happy birthday love watched think watching song concert their please can they these his her who new favorite favourite should",
    "es": "hola qué cómo cumpleaños feliz para una los las este esta quiero concierto cumpleaños canción gracias quien pienso nueva",
    "pt": "você vocês parabéns hoje eu uma não são gostei música muito obrigada obrigado estão também",
    "fr": "bonjour anniversaire joyeux vous pourquoi est-ce était merci cette concert-là chanson très quelle nouveau vraiment",
    "de": "ich und ist sind war nicht liebe wie warum das zum alles gute geburtstag konzert diese",
    "it": "ciao compleanno auguri questa questo perché molto davvero grazie canzone concerto quale",
    "id": "aku kamu lagu untuk yang banget ulang tahun mereka selamat konser suka",
    "nl": "jij deze zijn niet waarom heel geweldig gefeliciteerd verjaardag een",
    "tr": "bugün doğum günün mutlu olsun konseri şarkı çok bence",
}
VOCAB = {lang: set(words.split()) for lang, words in WORDS.items()}

def plain(value):
    return " ".join(unescape(str(value or "")).split())


def comparison(value):
    return unicodedata.normalize("NFKC", plain(value)).casefold()


def known_title(row):
    original = plain(row.get("title"))
    for candidate in (row.get("title_zh"), chinese_title(row)):
        text = plain(candidate)
        if HAN.search(text) and comparison(text) != comparison(original) and not MARKUP.search(text):
            return text
    return ""


def title_language(row):
    tagged = str(row.get("language") or row.get("lang") or "").strip().lower().replace("_", "-")
    if re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*", tagged):
        lang = tagged.split("-")[0]
        if lang not in {"und", "mul", "zxx"}:
            return lang
    text = plain(row.get("title"))
    if KANA.search(text):
        return "ja"
    if HANGUL.search(text):
        return "ko"
    if HAN.search(text):
        if "日本官网" in str(row.get("source", "")):
            return "ja"
        if "韩星网" in str(row.get("source", "")) or re.search(
            r"[们們這这话話发發团團爱愛欢歡觉覺吗嗎麼么们很你我给給为為听聽個让讓该该]"
            r"|生日快乐|生日快樂|分享|有谁|大家|音乐|組合|组合|生日祝福|演唱会|演唱會", text
        ):
            return "zh"
        return "und"
    for pattern, lang in ((r"[ก-๛]", "th"), (r"[Α-ω]", "el"), (r"[א-ת]", "he"),
                          (r"[Ա-ֆ]", "hy"), (r"[Ⴀ-ჿ]", "ka"), (r"[іІїЇєЄґҐ]", "uk"),
                          (r"[ыЫэЭъЪёЁ]", "ru"), (r"[đĐơƠưƯ]", "vi")):
        if re.search(pattern, text):
            return lang
    tokens = set(re.findall(r"[^\W\d_]+", text.casefold()))
    scores = sorted(((len(tokens & words), lang) for lang, words in VOCAB.items()), reverse=True)
    count, lang = scores[0]
    return lang if count >= 1 and count > scores[1][0] else "und"


def decoded_result(payload, original):
    if not isinstance(payload, dict):
        raise ValueError("MyMemory 返回了无法读取的翻译结果。")
    status = str(payload.get("responseStatus"))
    if status == "429" or payload.get("quotaFinished") in (True, 1, "true"):
        raise ValueError("MyMemory 暂时限流或已达到今日免费额度，请稍后再试。")
    if status != "200":
        raise ValueError("MyMemory 暂时无法翻译这个标题。")
    data = payload.get("responseData")
    translated = plain(data.get("translatedText")) if isinstance(data, dict) else ""
    if (not HAN.search(translated) or comparison(translated) == comparison(original)
            or MARKUP.search(translated) or len(translated) > 6 * len(original) + 60):
        raise ValueError("翻译服务没有返回可用的中文译文，请查看原文。")
    # Translation memories can return a near match from a different source sentence.
    matches = payload.get("matches")
    if isinstance(matches, list):
        selected = [m for m in matches if isinstance(m, dict)
                    and comparison(m.get("translation")) == comparison(translated) and m.get("segment")]
        if selected and all(comparison(m["segment"]) != comparison(original) for m in selected):
            raise ValueError("MyMemory 只找到了相似句子，暂时无法提供这条标题的可靠译文。")
    return translated


def translate_title(row):
    """Raise ValueError with a displayable Chinese message when no translation is available."""
    existing = known_title(row)
    if existing:
        return existing
    language = title_language(row)
    if language == "zh":
        raise ValueError("这个标题已经是中文。")
    if language == "und":
        raise ValueError("标题太短或语种不明确，暂时无法可靠翻译。")
    title = plain(LINK_OR_HANDLE.sub(" ", plain(row.get("title"))))
    if not title or MARKUP.search(title):
        raise ValueError("标题中没有可单独翻译的纯文本。")
    if len(title.encode("utf-8")) > 500:
        raise ValueError("这个标题超过 MyMemory 单次 500 字节的限制。")
    query = urlencode({"q": title, "langpair": f"{language}|zh-CN"})
    request = Request(API + "?" + query, headers={"User-Agent": "NextdoorLetter/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=6) as response:
            body = response.read(128001)
    except HTTPError as error:
        if error.code == 429:
            raise ValueError("MyMemory 暂时限流或已达到今日免费额度，请稍后再试。") from None
        raise ValueError(f"MyMemory 暂时无法提供翻译（HTTP {error.code}）。") from None
    except (OSError, HTTPException):
        raise ValueError("目前无法连接 MyMemory。联网后可以重试。") from None
    if len(body) > 128000:
        raise ValueError("MyMemory 返回的结果过大。")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise ValueError("MyMemory 返回了无法读取的翻译结果。") from None
    return decoded_result(payload, title)
