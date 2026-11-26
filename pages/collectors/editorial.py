"""Chinese reading notes for BOYNEXTDOOR's public announcements and videos."""

import re
import unicodedata
from html import unescape


MEMBERS = {
    "SUNGHO": ("성호", "ソンホ", "成淏", "朴成浩"),
    "RIWOO": ("리우", "リウ", "李常赫"),
    "JAEHYUN": ("재현", "ジェヒョン", "宰铉", "宰鉉"),
    "TAESAN": ("태산", "テサン", "泰山"),
    "LEEHAN": ("이한", "イハン", "李翰"),
    "WOONHAK": ("운학", "ウナク", "云鹤", "雲鶴"),
}


def key(text):
    text = unicodedata.normalize("NFKC", unescape(text or "")).casefold()
    # Several distinct videos have the same hashtags and only an emoji as their caption.
    return "".join(c for c in text if c.isalnum() or unicodedata.category(c).startswith("S"))


def member_names(title):
    names = []
    for member, aliases in MEMBERS.items():
        if (re.search(r"(?<![a-z])" + member + r"(?![a-z])", title, re.I)
                or any(name in title for name in aliases)):
            names.append(member)
    return names


# Notes refer to a specific headline. Punctuation and display spaces vary between feeds.
NOTES = {}


def note(original, headline, brief):
    NOTES[key(original)] = (headline, brief)


note("HYBE MUSIC GROUP MERCH POP-UP STORE開催決定！",
     "HYBE 宣布开设音乐厂牌周边快闪店", "BOYNEXTDOOR 日本官网发布了 HYBE MUSIC GROUP MERCH POP-UP STORE 的举办公告。")
note("\"Oops! It's WOONHAK's Birthday\" 販売決定！",
     "WOONHAK 生日企划「Oops! It's WOONHAK's Birthday」将开售", "这条生日企划公告来自日本官网，购买详情可查看原文。")
note("『BOYNEXTDOOR 2027 BLOCK CALENDAR』発売決定！11月20日(金)11:00より予約販売開始！",
     "BOYNEXTDOOR 2027 积木日历开放预订", "日本官网公布预购时间为 11 月 20 日日本时间 11:00，即北京时间 10:00。")
note("『BOYNEXTDOOR 2027 SEASON'S GREETINGS』発売決定！11月20日(金)11:00より予約販売開始！",
     "BOYNEXTDOOR 2027 年度问候礼盒开放预订", "2027 SEASON’S GREETINGS 于 11 月 20 日日本时间 11:00 开始预订，即北京时间 10:00。")
note("BOYNEXTDOOR 2026 Black Friday販売決定！",
     "BOYNEXTDOOR 公布 2026 黑色星期五销售企划", "日本官网发布了本年度 Black Friday 销售信息。")
note("One and Only Hoodie Merch.再販売決定！",
     "「One and Only」连帽衫周边将再次发售", "日本官网确认这款连帽衫周边将重新开售。")
note("11月にお誕生日を迎えるONEDOORのみなさんへのお祝いメッセージが到着！",
     "给 11 月生日的 ONEDOOR：生日祝福已送达", "日本官方粉丝俱乐部发布了送给本月寿星的祝福。")
note("HYBE CINE FEST 2026 OFFICIAL MERCHANDISE 発売決定！",
     "HYBE CINE FEST 2026 将发售官方周边", "电影节官方周边的商品与销售信息可在日本官网查看。")
note("BOYNEXTDOORを応援しよう！ 「HYBE CHEERING PARTY」全国の映画館にて11月5日(木)以降、毎週木曜日開催！入場者特典、3D上映も決定！",
     "HYBE 应援派对 11 月 5 日起每周四在日本影院举行", "官方同时公布了入场特典和 3D 放映安排。")
note("BOYNEXTDOOR X BBNEXDO POP-UP 'BBNEXDO in Sweet Dreams' 東京・大阪にて開催決定！",
     "「BBNEXDO in Sweet Dreams」快闪店将登陆东京与大阪", "BOYNEXTDOOR × BBNEXDO 联动快闪活动确认在日本两个城市举办。")
note("10月28日(水)発売『Oggi』2026年12月号にSUNGHOとLEEHANが登場！",
     "SUNGHO 和 LEEHAN 登上《Oggi》12 月号", "刊物于 10 月 28 日发售，登场的是 SUNGHO 与 LEEHAN 两位成员。")
note("9月27日(日) フジテレビ系列『突然ですが占ってもいいですか？』に出演決定！",
     "BOYNEXTDOOR 出演富士电视台占卜综艺", "9 月 27 日节目为《突然ですが占ってもいいですか？》。")
note("9月12日(土) NHK『Venue101』に生出演決定！",
     "BOYNEXTDOOR 参加 NHK《Venue101》直播", "日本官网将这场电视直播列在 9 月 12 日的行程中。")
note("9月11日(金) 日本テレビ系『バズリズム02』に出演決定！",
     "BOYNEXTDOOR 出演日本电视台《Buzz Rhythm 02》", "节目日文名为《バズリズム02》，官方行程日期为 9 月 11 日。")
note("9月7日(月)発売の『CREA』2026秋号【特別版】の表紙にSUNGHO、RIWOO、LEEHANが初登場！",
     "SUNGHO、RIWOO 和 LEEHAN 首登《CREA》特别版封面", "三人登上 2026 秋季号特别版封面，杂志于 9 月 7 日发售。")
note("8月17日(月) TBS系『CDTVライブ！ライブ！』に生出演決定！",
     "BOYNEXTDOOR 参加 TBS《CDTV LIVE! LIVE!》直播", "这场音乐节目直播列在 8 月 17 日的官方日程中。")
note("6月19日(金)発売『CUT』2026年7月号のバックカバーに決定！",
     "BOYNEXTDOOR 登上《CUT》7 月号封底", "这期 2026 年 7 月号杂志于 6 月 19 日发售。")
note("BOYNEXTDOORが「2026 Weverse Con Festival」に出演！",
     "BOYNEXTDOOR 亮相 2026 Weverse Con Festival", "日本官方网站将这场音乐节演出列入组合行程。")
note("5月26日(火) 日本テレビ系『夜の音-TOKYO MIDNIGHT MUSIC-』に出演決定！",
     "BOYNEXTDOOR 出演日本电视台《夜の音》", "节目全名为《夜の音 -TOKYO MIDNIGHT MUSIC-》，官方日程日期为 5 月 26 日。")
note("5月9日(土)『Kstyle PARTY 2026』に出演決定！",
     "BOYNEXTDOOR 登上 Kstyle PARTY 2026 舞台", "日本官网的活动日期为 5 月 9 日。")
note("입을 수 있는 걸 고르라고 제발!!!!!! (안 입힐 건데?) | DONEXTDOOR SPECIAL *Find Your MART MANITO*",
     "《DONEXTDOOR》特别篇：拜托，选件能穿的吧！", "这期特别篇名为「Find Your MART MANITO」。标题中的回应是「可是又没打算让你穿？」。")
note("Hollywood Action📸 #BOYNEXTDOOR #보이넥스트도어 #BND #KNOCK_ON_Vol_2_IN_NA#Hollywood_Action_Challenge",
     "《Hollywood Action》挑战：北美巡演篇", "组合官方频道发布了带有 KNOCK ON Vol.2 北美巡演标签的挑战视频。")
note("오늘도 힘넥도 | VIP 전담 케어 | EP03 - BOYNEXTDOOR (보이넥스트도어)",
     "《오늘도 힘넥도》第 3 集：VIP 专属照顾", "本期官方系列视频的主题是「VIP 专属照顾」。")
note("Cover | NUEVAYoL - JAEHYUN (원곡 : Bad Bunny)",
     "JAEHYUN 翻唱 Bad Bunny 的《NUEVAYoL》", "这段翻唱由 JAEHYUN 演绎，原唱为 Bad Bunny。")
note("Walk it like I talk it #BOYNEXTDOOR #보이넥스트도어 #BND #SUNGHO #KNOCK_ON_Vol_2_IN_NA",
     "SUNGHO 北美巡演短片「Walk it like I talk it」", "官方频道以 SUNGHO 和 KNOCK ON Vol.2 北美巡演为标签发布这段视频。")
note("Lo tiene' que move'-ve'-ve'-ve'-ve' #BOYNEXTDOOR #보이넥스트도어 #BND #JAEHYUN #KNOCK_ON_Vol_2_IN_NA",
     "JAEHYUN 北美巡演短片「Lo tiene’ que move’」", "这条以西语歌词为题的短视频带有 JAEHYUN 与北美巡演标签。")
note("Corazón, Me gustas 😘 #TACOSATARANTADOS #MUKBANG #BOYNEXTDOOR #보이넥스트도어 #KNOCK_ON_Vol_2_in_USA",
     "美国巡演吃播：来一份塔可", "官方以西语「Corazón, me gustas」配文，并标注了 TACOSATARANTADOS 和吃播标签。")
note("L-O-V-E is 🎄#BOYNEXTDOOR #보이넥스트도어 #BND #BND_2027시즌그리팅 #MONSTER_TROUBLE_LAUNDRY",
     "2027 年度问候短片：L-O-V-E 与圣诞树", "这是「MONSTER TROUBLE LAUNDRY」年度问候企划的短视频。")
note("흥! #BOYNEXTDOOR #보이넥스트도어 #BND #TAESAN #KNOCK_ON_Vol_2_IN_NA",
     "TAESAN 北美巡演短片「哼！」", "官方频道发布了带有 TAESAN 与 KNOCK ON Vol.2 北美巡演标签的视频。")
note("운피까 ʕ◍꜆·̀Ⱉ·́꜀◍ʔ #BOYNEXTDOOR #보이넥스트도어 #BND #WOONHAK #KNOCK_ON_Vol_2_IN_NA",
     "WOONHAK 的北美巡演短片「운피까」", "视频标题配了一只小动物颜文字，官方标签注明成员为 WOONHAK。")
note("거리에서? 우연히?? 닭을??? 만났습니다????? | DONEXTDOOR in MIAMI",
     "《DONEXTDOOR》迈阿密篇：在街上偶遇了一只鸡？", "这期迈阿密特辑把一次街头偶遇写进了标题。")
note("찾았다 한태산 #BOYNEXTDOOR #보이넥스트도어 #BND #BOYNEXTDOOR_123_78 #12378_Challenge",
     "「找到 TAESAN 了！」组合发布 123-78 挑战短片", "TAESAN 的名字出现在视频标题中，话题为 12378 Challenge。")
note("솔로인 친구에게 공유하세요 #BOYNEXTDOOR #보이넥스트도어 #BND #BOYNEXTDOOR_123_78 #12378_Challenge",
     "「分享给你单身的朋友」：123-78 挑战短片", "组合为这条挑战视频写下了送给单身朋友的配文。")
note("𝓻𝓸𝓬𝓴𝓼𝓽𝓪𝓻🎸#BOYNEXTDOOR #보이넥스트도어 #BND #BND_2027시즌그리팅 #MONSTER_TROUBLE_LAUNDRY",
     "2027 年度问候短片：摇滚明星与吉他", "官方频道以「rockstar🎸」配文，发布年度问候企划的新短片。")
note("❤️‍🔥#BOYNEXTDOOR #보이넥스트도어 #BND #BND_2027시즌그리팅 #MONSTER_TROUBLE_LAUNDRY",
     "2027 年度问候短片：燃烧的爱心", "这条「MONSTER TROUBLE LAUNDRY」系列短视频以燃烧的爱心表情配文。")


VIDEO_FORMATS = [
    (r"(?:official\s+)?(?:music video|m/?v)\s+teaser", "MV 预告"),
    (r"(?:official\s+)?(?:music video|m/?v)", "音乐视频"),
    (r"(?:official\s+)?dance practice(?:\s+video)?", "舞蹈练习室"),
    (r"(?:official\s+)?performance (?:video|film)", "表演视频"),
    (r"(?:official\s+)?(?:lyric|lyrics) video", "歌词视频"),
    (r"(?:official\s+)?highlight medley", "专辑试听串烧"),
]


def future_title(title):
    # Only substitute an explicit programme or video format; leave names and qualifiers intact.
    programme = re.fullmatch(r"(\d{1,2}月\d{1,2}日)(?:[（(][月火水木金土日][）)])?\s*([^『「]*?)[『「](.+?)[』」]に(生)?出演決定[!！]?", title)
    if programme:
        day, channel, show, live = programme.groups()
        headline = f"BOYNEXTDOOR {'参加' if live else '出演'}《{show}》{'直播' if live else ''}"
        return headline, f"官方日程为 {day}。" + (f"播出平台：{channel}。" if channel else "")
    birthday = re.fullmatch(r"(\d{1,2})月にお誕生日を迎えるONEDOORのみなさんへのお祝いメッセージが到着[！!]?", title)
    if birthday:
        return f"给 {birthday[1]} 月生日的 ONEDOOR：生日祝福已送达", ""
    for pattern, label in VIDEO_FORMATS:
        translated, count = re.subn(r"\b" + pattern + r"\b", label, title, count=1, flags=re.I)
        if count:
            return translated, ""
    return "", ""


def enrich(row):
    """Keep the complete original row and attach conservative Chinese reading notes."""
    title = unescape(row.get("title") or "").strip()
    normalized = unicodedata.normalize("NFKC", title)
    translated, brief = NOTES.get(key(title)) or future_title(normalized)
    if row.get("start_at") and key(title) == key("HYBE MUSIC GROUP MERCH POP-UP STORE開催決定！"):
        translated = "涩谷 · HYBE 音乐厂牌周边快闪店"
        brief = "这场东京涩谷的快闪活动展售 HYBE 旗下厂牌的艺人周边。"
    return dict(row, title_zh=translated or title, summary_zh=brief, members=member_names(normalized))
