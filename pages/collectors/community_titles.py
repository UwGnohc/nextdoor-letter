"""Chinese display titles for verified public discussion headlines."""

from hashlib import sha256


# Keys are 96 bits of SHA-256 of the exact UTF-8 source title. Revised titles fall back
# to the original, and the translation table stores neither user handles nor post text.
TRANSLATIONS = {
    "981b1c317b480f75302dfc08": "BOYNEXTDOOR 的《ANIMAL》🩶",
    "55f82857091aa048c923ce48": "RIWOO，生日快乐！🥳🩵",
    "b1129c678eb666a690b723cb": "祝 RIWOO 生日快乐！🎂🎉",
    "f75351346401f5edf9b9a684": "祝 BOYNEXTDOOR 的「海洋王子」LEEHAN 生日快乐！",
    "4dcbe1021855bb5c8eb3114e": "还想再分享一个合作舞台：WOONHAK、韩维辰和 TWS 成员等人",
    "b35e7253fabac4d2518188c3": "重温 2023 MAMA《Endless Rain》合作舞台：YOSHIKI、JAEHYUN 等",
    "113de7b68e3eee6de449300a": "一起看 CHANELLE MOON、YEWON 和 TAESAN 的《GAME START》",
    "c1afc4f5d77b5967fd17d3a8": "ATHENA 和 WOONHAK 的《POOKIE》挑战",
    "c1f5b6a3e6bb796e6bddff4c": "想参加 BOYNEXTDOOR 歌曲对决吗？谁想收到提醒？",
    "56ffdd2909d0b1b630d47501": "《WHAT? DOOR!》第 13 集：组队上岛求生，这是天堂吗？",
    "0703a8fa50cc93cd433b217f": "重看《400 Years》在 ONEDOORful Day 的舞台录像",
    "2694ffcd3bce369e1f2d4649": "《BEHINDOOR》第 20 集：走进 2024 KCON 日本站幕后",
    "1ae0faef4e4e1361a4b42775": "《WHAT? DOOR!》第 11 集：神秘医院里只剩我们了？",
    "879fd719b0b8d3b90f2fa8a1": "《CAMCORDOOR》分享：出道前未公开的 Vlog",
    "87e77e723c80045d31a06870": "重温 BOYNEXTDOOR 一周年派对「DOORJANCHI」",
    "bcc7eb7f6d240044f53a730a": "《WHAT? DOOR!》预告：我们被困在医院了",
    "8e329453541bd395f122737a": "BOYNEXTDOOR 官方应援棒怎么用？来看使用指南",
    "427f79affad3fd3891ff6eaf": "日本首张单曲《AND,》概念短片：「夜行」版",
    "135f1c6a48bf31a6af6e3c7c": "视频分享：BOYNEXTDOOR 寻找「真正的老师」",
    "75b3957428ab30f6e5f2253c": "《DOORGROUND》加映片段：一起听《l i f e i s c o o l》",
    "ead65d93051c264249e71d47": "《BEHINDOOR》第 13 集：《HOW?》现场演唱舞蹈练习花絮",
    "6afe26c606f539b9c48b0ddc": "一起学 BOYNEXTDOOR《OUR》的应援口号",
}


WORLD_TRANSLATIONS = {
    "note · BOYNEXTDOOR": {
        "b79f31554adc0d37a27f9ddf": "《乐园 Vol.2》千叶场第一天",
        "d6995c5cf25deb3e2e213a83": "BOYNEXTDOOR《Count To Love》韩语版歌词的日语翻译",
        "9e52574057396ee675e5baa6": "BOYNEXTDOOR《KNOCK ON Vol.2》日本巡演首日：2026 年 8 月 21 日，横滨 K-Arena",
        "c5b0f8d42e90ac0bbfdcc68c": "续篇：我为什么这么喜欢 BOYNEXTDOOR 的专辑收录曲？《KNOCK ON Vol.2》的余韵",
        "c0ea9139513f036580bb34e4": "日本 6 场、加拿大 2 场：看完 BOYNEXTDOOR《KNOCK ON Vol.2》八场演出的回顾",
        "5726aed3b4142ad3c37899c9": "大阪连看两天！",
        "311a165871b839cc8e0373d1": "猜猜 2026 Music Bank 日本全球音乐节的歌单：LE SSERAFIM、BOYNEXTDOOR、CORTIS",
        "f749578fbfa620f86f267a9d": "BOYNEXTDOOR《HOME: DELUXE》各版本有什么区别？写给新入坑的你",
        "d29973a5316ebd4d8c86a703": "最近迷上了 BOYNEXTDOOR 的 SUNGHO",
        "2376217e1ff91a81cf28fff4": "在一路奔跑的乐园里，我找到了自己的幸福：BOYNEXTDOOR《KNOCK ON Vol.2》千叶场与《ANIMAL》感想",
    },
    "FanPlus · BOYNEXTDOOR": {
        "d5921a4ef3a8447975192b3f": "明宰铉在纽约街头拍的照片，氛围感满满",
        "bb4d44dd891b007eed2a09e2": "BOYNEXTDOOR《KNOCK ON Vol.2》墨西哥城演出照片",
        "0ed47758b94a80c9db731372": "边吃塔可边拍照，明宰铉和 TAESAN 的照片很有 Z 世代的味道",
        "68111e7c89ab131501b97282": "TAESAN 展现「海洋王子」的一刻",
        "4a87d104690f0b1cbf50bd89": "明宰铉送上翻唱 Bad Bunny《NUEVAYoL》的视频",
        "6a4a44a29bcc79915b085c80": "看看 WOONHAK 在洛杉矶的自拍，今天也要过得开心",
        "feb6834cd5986f3af2e0273f": "RIWOO 分享了在迈阿密拍的照片",
        "a73e905fdbeb7e550c9e4601": "RIWOO 今天也拍了超可爱的自拍",
        "f03bd2f8a972fd3acf6aed03": "明宰铉这张自拍，帅到让人心动",
        "bda98c37b787f2277f14e6c3": "看了 LEEHAN 的《The Puppy Interview》照片，既羡慕小狗，也羡慕他",
        "0631bc19cf9b0ee61230ca47": "千叶演出前的「狸猫打工」第二天，RIWOO 进步飞快",
        "820bcada9879edf83354ea7d": "BOYNEXTDOOR 的提前下班应援大作战：亲自把老大送下班",
        "ede90e36ce920c324cd084d9": "BOYNEXTDOOR 的 One and Only 连帽衫要再开售了",
        "cb63094f03feface9686a189": "日本电影院的应援放映也能看到 BOYNEXTDOOR 的视频",
        "7395fc75273d3f3e8164249f": "BOYNEXTDOOR 日本黑五活动 20 日开始",
        "0b16ec97b88568e4432b3789": "BOYNEXTDOOR 将推出 2027 年日历「BLOCK CALENDAR」",
        "9a8ec0684e5f8bda2014f4e4": "BOYNEXTDOOR 将推出 2027 Season’s Greetings 新年礼包",
        "816eb1002ac412884288272b": "BOYNEXTDOOR 2027 Season’s Greetings 新年礼包首组预告照",
        "d13253ce9ecd34b0496d8ed2": "SUNGHO 的粉发造型好可爱，来看看照片",
        "dc227b89a217a05ec40de28a": "长发配西装太适合 LEEHAN 了，来看看这组照片",
    },
}


def chinese_title(row):
    title = row.get("title") or ""
    source = row.get("source")
    digest = sha256(title.encode("utf-8")).hexdigest()[:24]
    if source in WORLD_TRANSLATIONS:
        return WORLD_TRANSLATIONS[source].get(digest, title)
    if source in {"K-Pop Source", "Mastodon"}:
        return TRANSLATIONS.get(digest, title)
    return title
