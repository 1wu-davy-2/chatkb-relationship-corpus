#!/usr/bin/env python3
"""Collect Chinese public materials, Wikipedia extracts, and open-source skills.

Copyright policy:
- Wikipedia: CC BY-SA 4.0, full extract with attribution.
- Laws / official notices: full text, public official documents.
- Media / university / commercial articles: short excerpt only, for personal
  research; the full article stays at the original link.
- GitHub skills: full text only when the repository has a permissive license.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW_ZH = ROOT / "01_raw" / "zh_official"
RAW_WIKI = ROOT / "01_raw" / "zh_wikipedia"
RAW_SKILLS = ROOT / "01_raw" / "skills"
TEXT_ZH = ROOT / "02_text" / "zh_official"
TEXT_WIKI = ROOT / "02_text" / "zh_wikipedia"
TEXT_SKILLS = ROOT / "02_text" / "skills"
RECORDS = ROOT / "05_manifest" / "records"
LOG_PATH = ROOT / "05_manifest" / "fetch_zh.log"
USER_AGENT = "ChatKBResearch/1.0 (personal study corpus; local use)"

for d in (RAW_ZH, RAW_WIKI, RAW_SKILLS, TEXT_ZH, TEXT_WIKI, TEXT_SKILLS, RECORDS):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("zh")

# One row per article. A requested title that zh Wikipedia does not host under
# that name used to be resolved by a prefix search, which silently produced
# wrong articles (压力 -> 压强 "pressure" in physics, 婚俗 -> 印度教婚俗, 互惠 ->
# 互惠生 "au pair"). The fallback now demands an exact normalised match, and the
# remaining wrong articles from the old behaviour were dropped with
# tools/dedupe_wiki.py; the replacements above were each checked with
# tools/probe_wiki_titles.py before being fetched.
WIKI = [
    # 心理学与沟通基础
    ("attachment_theory", "依恋理论", ["attachment", "emotion", "psychology"]),
    ("nonviolent_communication", "非暴力沟通", ["communication", "conflict"]),
    ("interpersonal_communication", "人际沟通", ["communication", "skills"]),
    ("nonverbal_communication", "非语言沟通", ["communication", "nonverbal"]),
    ("body_language", "肢体语言", ["nonverbal", "communication"]),
    ("empathy", "共情", ["empathy", "communication"]),
    ("active_listening", "積極聆聽", ["listening", "communication"]),
    ("persuasion", "说服", ["communication", "influence"]),
    ("negotiation", "谈判", ["communication", "conflict"]),
    ("conflict_resolution", "衝突解決", ["conflict", "communication"]),
    ("conflict_management", "冲突管理", ["conflict", "communication"]),
    ("apology", "道歉", ["conflict", "repair"]),
    ("forgiveness", "宽恕", ["conflict", "repair"]),
    ("gratitude", "感恩", ["emotion", "relationship"]),
    ("humor", "幽默", ["communication", "attraction"]),
    ("self_disclosure", "自我揭露", ["communication", "intimacy"]),
    ("emotion_regulation", "情绪调节", ["emotion", "skills"]),
    ("emotional_intelligence", "情绪智力", ["emotion", "skills"]),
    ("psychological_resilience", "心理韧性", ["emotion", "wellbeing"]),
    ("mindfulness", "正念", ["emotion", "wellbeing"]),
    ("self_compassion", "自我关怀", ["emotion", "wellbeing"]),
    ("self_esteem", "自尊", ["self_esteem", "psychology"]),
    ("self_confidence", "自信", ["self_esteem", "psychology"]),
    ("social_skills", "社交技巧", ["social_skills", "communication"]),
    ("shyness", "害羞", ["personality", "social_anxiety"]),
    ("social_anxiety", "社交焦虑", ["anxiety", "social"]),
    ("social_anxiety_disorder", "社交焦虑障碍", ["anxiety", "social"]),
    ("loneliness", "孤独", ["loneliness", "emotion"]),
    ("depression", "抑郁症", ["mental_health"]),
    ("anxiety", "焦虑", ["mental_health"]),
    ("stress", "心理压力", ["mental_health", "stress"]),
    ("stress_response", "应激", ["mental_health", "stress"]),
    ("mental_health", "心理健康", ["mental_health"]),
    ("psychological_counseling", "心理咨询", ["mental_health", "help"]),
    ("psychotherapy", "心理治疗", ["mental_health", "help"]),
    ("cognitive_behavioral_therapy", "认知行为疗法", ["mental_health", "help"]),
    ("confirmation_bias", "确认偏误", ["cognition", "bias"]),
    ("cognitive_bias", "认知偏差", ["cognition", "bias"]),
    ("barnum_effect", "巴纳姆效应", ["cognition", "bias", "astrology"]),
    # 爱情、约会与关系
    ("love", "爱情", ["love", "psychology"]),
    ("five_love_languages", "愛的五種語言", ["love", "relationship"]),
    ("sternberg", "罗伯特·斯腾伯格", ["love", "psychology"]),
    ("passion", "激情", ["love", "attraction"]),
    ("commitment", "承诺", ["relationship", "commitment"]),
    ("intimacy", "亲密关系", ["intimacy", "relationship"]),
    ("interpersonal_relationship", "人际关系", ["relationship", "communication"]),
    ("courtship", "求偶", ["courtship", "dating"]),
    ("dating", "約會", ["dating", "courtship"]),
    ("online_dating", "網路交友", ["online_dating", "technology"]),
    ("long_distance_relationship", "异地恋", ["relationship", "distance"]),
    ("breakup", "分手", ["breakup", "relationship"]),
    ("unrequited_love", "暗恋", ["attraction", "rejection"]),
    ("jealousy", "嫉妒", ["emotion", "relationship"]),
    ("trust", "信任", ["trust", "relationship"]),
    ("marriage", "婚姻", ["marriage", "family"]),
    ("monogamy", "一夫一妻制", ["marriage", "society"]),
    ("wedding", "婚礼", ["marriage", "culture"]),
    ("divorce", "离婚", ["divorce", "relationship"]),
    ("extramarital_affair", "婚外情", ["infidelity", "relationship"]),
    ("premarital_sex", "婚前性行为", ["sexuality", "society"]),
    ("sexual_consent", "性同意", ["consent", "sexuality"]),
    ("sexual_harassment", "性骚扰", ["safety", "harassment"]),
    ("domestic_violence", "家庭暴力", ["abuse", "safety"]),
    ("cold_violence", "冷暴力", ["abuse", "safety"]),
    # 边界、操控与安全
    ("personal_boundaries", "个人边界", ["boundaries", "relationship"]),
    ("emotional_labor", "情绪劳动", ["boundaries", "emotion"]),
    ("codependency", "共依存症", ["boundaries", "relationship"]),
    ("people_pleasing", "取悅症", ["personality", "boundaries"]),
    ("emotional_blackmail", "情緒勒索", ["abuse", "boundaries"]),
    ("gaslighting", "煤气灯效应", ["abuse", "manipulation"]),
    ("psychological_manipulation", "心理操纵", ["manipulation", "safety"]),
    ("brainwashing", "洗脑", ["manipulation", "safety"]),
    ("coercive_control", "強制控制", ["abuse", "control"]),
    ("stalking", "跟踪骚扰", ["safety", "harassment"]),
    ("narcissism", "自恋", ["personality", "abuse"]),
    ("narcissistic_personality_disorder", "自恋型人格障碍", ["personality", "abuse"]),
    ("antisocial_personality_disorder", "反社会人格障碍", ["personality", "safety"]),
    ("dark_triad", "黑暗三角人格", ["personality", "safety"]),
    ("pickup_artist", "搭讪艺术家", ["pua", "manipulation"]),
    ("romance_scam", "杀猪盘", ["scam", "money", "online_dating"]),
    ("telecom_fraud", "电信诈骗", ["scam", "fraud"]),
    ("online_fraud", "网络诈骗", ["scam", "fraud"]),
    ("money_laundering", "洗钱", ["fraud", "money"]),
    ("ponzi_scheme", "庞氏骗局", ["fraud", "money"]),
    ("pyramid_scheme", "传销", ["fraud", "money"]),
    ("extortion", "敲诈勒索", ["fraud", "safety"]),
    ("privacy", "隐私", ["safety", "privacy"]),
    ("personal_information_protection", "个人信息保护", ["safety", "privacy"]),
    # 人格与分类工具（只作为破冰话题，不作为预测）
    ("astrology", "占星学", ["astrology", "pseudoscience"]),
    ("zodiac", "星座", ["astrology", "culture"]),
    ("chinese_zodiac", "十二生肖", ["culture", "astrology"]),
    ("myers_briggs", "迈尔斯-布里格斯类型指标", ["mbti", "personality"]),
    ("big_five", "五大性格特质", ["personality", "psychology"]),
    ("personality_psychology", "人格心理学", ["personality", "psychology"]),
    ("extraversion", "外向", ["personality"]),
    ("highly_sensitive_person", "高敏感人格", ["personality", "emotion"]),
    # 中国社会与文化语境
    ("bride_price", "彩礼", ["marriage", "money", "china"]),
    ("dowry", "嫁妆", ["marriage", "money", "china"]),
    ("blind_date", "相亲", ["dating", "china", "matchmaking"]),
    ("leftover_women", "剩女", ["gender", "china", "marriage"]),
    ("leftover_men", "剩男", ["gender", "china", "marriage"]),
    ("marriage_pressure", "逼婚", ["marriage", "china", "family"]),
    ("marriage_squeeze", "婚姻挤压", ["marriage", "china", "demography"]),
    ("dink", "丁克", ["marriage", "china", "family"]),
    ("filial_piety", "孝道", ["culture", "family"]),
    ("confucianism", "儒家", ["culture", "values"]),
    ("mianzi", "面子", ["culture", "social"]),
    ("renqing", "人情", ["culture", "social"]),
    ("guanxi", "关系", ["culture", "social"]),
    ("social_capital", "社会资本", ["society", "social"]),
    ("gender_roles", "性别角色", ["gender", "society"]),
    ("gender_identity", "性别认同", ["gender", "identity"]),
    ("transgender", "跨性别", ["gender", "sexual_minorities"]),
    ("gender_equality", "性别平等", ["gender", "society"]),
    ("feminism", "女性主义", ["gender", "society"]),
    ("masculinity", "男性气质", ["gender", "society"]),
    ("patriarchy", "父权", ["gender", "society"]),
    ("consumerism", "消费主义", ["money", "values"]),
    ("gift", "礼物", ["money", "relationship"]),
    ("gift_economy", "礼物经济", ["money", "society"]),
    ("personal_finance", "个人理财", ["money", "skills"]),
    ("debt", "债务", ["money", "safety"]),
    ("fertility_rate", "生育率", ["demography", "marriage"]),
    ("sex_ratio", "性别比", ["demography", "marriage"]),
    ("urbanization", "城市化", ["society", "demography"]),
    # 科技与线上互动
    ("social_media", "社交媒体", ["technology", "social"]),
    ("social_network_service", "社交网络服务", ["technology", "social"]),
    ("instant_messaging", "即时通讯", ["technology", "communication"]),
    ("wechat", "微信", ["technology", "communication", "china"]),
    ("smartphone_addiction", "智能手机成瘾", ["technology", "wellbeing"]),
    ("phubbing", "低头族", ["technology", "relationship"]),
    ("chatbot", "聊天机器人", ["technology", "ai"]),
]

# Second batch: alternates for titles that redirected to stubs, plus deeper
# coverage of the psychology / law / money / online-safety layers.
WIKI += [
    # 上一批失败条目的替代标题
    ("conflict_management", "衝突管理", ["conflict", "communication"]),
    ("negotiation", "谈判", ["negotiation", "communication"]),
    ("self_compassion", "自我關懷", ["self_compassion", "wellbeing"]),
    ("highly_sensitive_person", "高敏感族群", ["personality"]),
    ("mobile_phone_addiction", "手機成癮", ["technology", "wellbeing"]),
    ("people_pleasing", "討好型人格", ["personality", "boundaries"]),
    ("resilience", "复原力", ["psychology", "wellbeing"]),
    ("clinical_depression", "重性抑郁障碍", ["mental_health"]),
    ("forced_marriage_pressure", "催婚", ["china", "family"]),
    ("pyramid_scheme", "層壓式推銷", ["scam", "money"]),
    ("extortion", "恐嚇", ["law", "safety"]),
    ("persuasion_alt", "劝说", ["communication", "influence"]),
    ("guanxi", "關係 (社會學)", ["culture", "china", "social"]),
    ("intimate_partner_violence", "親密伴侶暴力", ["abuse", "safety"]),
    # 沟通与社交技巧
    ("conversation", "对话", ["communication"]),
    ("small_talk", "闲聊", ["conversation", "skills"]),
    ("interpersonal_attraction", "人际吸引", ["attraction", "psychology"]),
    ("eye_contact", "眼神接触", ["nonverbal", "communication"]),
    ("etiquette", "礼仪", ["manners", "culture"]),
    ("praise", "赞美", ["communication", "skills"]),
    ("criticism", "批评", ["communication", "conflict"]),
    ("feedback", "反馈", ["communication", "workplace"]),
    ("assertiveness", "果斷行為", ["communication", "boundaries"]),
    ("public_speaking", "公众演讲", ["skills", "anxiety"]),
    ("storytelling", "讲故事", ["skills", "conversation"]),
    ("flirting", "调情", ["dating", "communication"]),
    ("friendship", "友谊", ["relationship"]),
    ("platonic_love", "柏拉圖式戀愛", ["love"]),
    ("limerence", "痴恋", ["love", "psychology"]),
    ("read_receipt_culture", "已读不回", ["communication", "dating"]),
    ("internet_slang", "网络用语", ["culture", "language"]),
    ("emoji", "表情符号", ["communication", "technology"]),
    ("text_message", "簡訊", ["communication", "technology"]),
    # 心理学机制（吸引、影响、判断）
    ("first_impression", "第一印象", ["psychology", "social"]),
    ("halo_effect", "光环效应", ["psychology", "bias"]),
    ("mere_exposure_effect", "多看效应", ["psychology", "attraction"]),
    ("physical_attractiveness", "外貌吸引力", ["attraction", "psychology"]),
    ("foot_in_the_door", "登门槛效应", ["psychology", "influence"]),
    ("obedience", "服从", ["psychology", "influence"]),
    ("milgram_experiment", "米尔格拉姆实验", ["psychology"]),
    ("peer_pressure", "同侪压力", ["psychology", "social"]),
    ("self_fulfilling_prophecy", "自证预言", ["psychology"]),
    ("attribution", "归因", ["psychology"]),
    ("fundamental_attribution_error", "基本归因错误", ["psychology", "bias"]),
    ("bystander_effect", "旁觀者效應", ["psychology", "safety"]),
    ("victim_blaming", "責怪受害者", ["safety", "psychology"]),
    ("ostracism", "社会排斥", ["social", "psychology"]),
    ("emotional_contagion", "情绪感染", ["emotion"]),
    ("social_exchange_theory", "社会交换理论", ["sociology", "relationship", "money"]),
    ("equity_theory", "公平理论", ["psychology", "relationship"]),
    ("evolutionary_psychology", "进化心理学", ["psychology"]),
    ("social_intelligence", "社会智能", ["psychology"]),
    ("alexithymia", "述情障碍", ["psychology", "emotion"]),
    ("self_concept", "自我概念", ["psychology"]),
    ("identity", "身份认同", ["psychology"]),
    ("body_image", "身体形象", ["psychology", "wellbeing"]),
    ("shame", "羞耻", ["emotion"]),
    ("anger", "愤怒", ["emotion"]),
    ("anger_management", "愤怒管理", ["emotion", "skills"]),
    ("regret", "后悔", ["emotion"]),
    ("mood", "心境", ["emotion"]),
    ("happiness", "幸福", ["psychology", "wellbeing"]),
    ("coping", "因应", ["psychology", "stress"]),
    ("meditation", "冥想", ["wellbeing", "psychology"]),
    ("self_care", "自我照顾", ["wellbeing", "mental_health"]),
    ("crisis_intervention", "危机干预", ["mental_health", "safety"]),
    ("suicide_prevention", "自杀预防", ["mental_health", "safety"]),
    ("addiction", "成瘾", ["psychology", "risk"]),
    # 人格与临床
    ("borderline_personality_disorder", "边缘型人格障碍", ["personality", "mental_health"]),
    ("avoidant_personality_disorder", "回避型人格障碍", ["personality"]),
    ("family_therapy", "家庭治疗", ["therapy", "family"]),
    ("couple_therapy", "伴侣治疗", ["therapy", "relationship"]),
    ("love_bombing", "愛情轟炸", ["manipulation", "safety"]),
    # 代表性研究者与著作
    ("john_bowlby", "约翰·鲍尔比", ["psychology", "attachment"]),
    ("erich_fromm", "埃里希·弗罗姆", ["psychology", "love"]),
    ("the_art_of_loving", "爱的艺术", ["book", "love"]),
    # 家庭、婚恋与中国社会
    ("family_of_origin", "原生家庭", ["family", "psychology", "china"]),
    ("mother_in_law_conflict", "婆媳关系", ["family", "china"]),
    ("domestic_labor", "家务分工", ["family", "gender"]),
    ("dual_income_family", "双薪家庭", ["family", "money"]),
    ("cohabitation", "同居", ["relationship"]),
    ("infidelity", "不忠", ["marriage", "relationship"]),
    ("arranged_marriage", "包办婚姻", ["marriage", "culture"]),
    ("marriage_custom_reform", "婚俗改革", ["china", "policy", "money"]),
    ("family_planning", "计划生育", ["china", "family"]),
    ("work_life_balance", "工作生活平衡", ["lifestyle", "career"]),
    ("single_lifestyle", "单身", ["lifestyle", "relationship"]),
    ("small_town_youth", "小镇青年", ["culture", "china"]),
    ("subculture", "亚文化", ["culture"]),
    ("herbivore_men", "草食男", ["culture", "gender"]),
    ("involuntary_celibacy", "非自愿单身", ["subculture", "gender"]),
    ("femininity", "女性气质", ["gender"]),
    ("toxic_masculinity", "有毒的男子气概", ["gender"]),
    ("sexism", "性别歧视", ["gender"]),
    ("misogyny", "厭女", ["gender"]),
    # 金钱、诈骗与法律
    ("savings", "储蓄", ["money"]),
    ("investment", "投资", ["money", "risk"]),
    ("gambling", "赌博", ["risk", "money"]),
    ("fraud", "诈骗", ["law", "scam"]),
    ("identity_theft", "身份盗窃", ["scam", "safety"]),
    ("phishing", "网络钓鱼", ["scam", "safety"]),
    ("money_mule", "人头账户", ["scam", "law"]),
    ("credit_reporting", "征信", ["money", "law"]),
    ("telecom_fraud", "電信網路詐騙", ["scam", "law"]),
    ("cyberbullying", "网络霸凌", ["safety", "online"]),
    ("revenge_porn", "报复式色情", ["safety", "law"]),
    ("live_streaming", "网络直播", ["technology", "money"]),
    ("parasocial_relationship", "拟社会关系", ["psychology", "media"]),
    ("online_community", "网络社区", ["technology", "social"]),
    ("ai_companion", "AI伴侣", ["technology", "relationship"]),
    ("civil_code_prc", "中华人民共和国民法典", ["law"]),
    ("marriage_law_prc", "中华人民共和国婚姻法", ["law", "history"]),
    ("women_protection_law", "妇女权益保障法", ["law", "gender"]),
    ("anti_telecom_fraud_law", "反电信网络诈骗法", ["law", "scam"]),
    ("public_security_punishment_law", "治安管理处罚法", ["law"]),
    ("criminal_law_prc", "中华人民共和国刑法", ["law"]),
    ("prenuptial_agreement", "婚前协议", ["law", "money"]),
    ("marital_property", "夫妻共同财产", ["law", "money"]),
    ("personal_safety_protection_order", "人身安全保护令", ["law", "safety"]),
    ("alimony", "赡养费", ["law", "family"]),
]

# Third batch (2026-10-26): human sexuality as a scholarly/health/communication
# subject, and astrology / fortune-telling studied as a belief phenomenon.
# Nothing here teaches "how to read a person from their birth chart"; the
# psychology entries (Barnum, confirmation bias, cold reading) exist precisely
# to explain why such readings feel accurate.
WIKI += [
    # 性学 / 人类性行为科学（学术与健康视角，非露骨内容）
    ("sexology", "性学", ["sexuality", "science"]),
    ("human_sexual_activity", "人类性行为", ["sexuality", "science"]),
    ("sexual_response_cycle", "人类性反应周期", ["sexuality", "physiology"]),
    ("sexual_health", "性健康", ["sexuality", "health"]),
    ("safer_sex", "安全性行為", ["sexuality", "health", "communication"]),
    ("libido", "性欲", ["sexuality", "desire"]),
    ("sexual_dysfunction", "性功能障碍", ["sexuality", "health"]),
    ("erectile_dysfunction", "勃起功能障碍", ["sexuality", "health"]),
    ("premature_ejaculation", "早泄", ["sexuality", "health"]),
    ("orgasm", "性高潮", ["sexuality", "physiology"]),
    ("sex_therapy", "性治療", ["sexuality", "therapy"]),
    ("sexual_orientation", "性取向", ["sexuality", "identity"]),
    ("asexuality", "无性恋", ["sexuality", "identity"]),
    ("sexual_minorities", "性少数群体", ["sexuality", "respect"]),
    ("contraception", "避孕", ["sexuality", "health", "decision"]),
    ("hiv_aids", "艾滋病", ["sexuality", "health", "stigma"]),
    ("pornography", "色情", ["sexuality", "media"]),
    ("porn_addiction", "色情成癮", ["sexuality", "addiction"]),
    ("sex_education", "性教育", ["sexuality", "education"]),
    ("comprehensive_sexuality_education", "全面性教育", ["sexuality", "education"]),
    ("kinsey_report", "金赛报告", ["sexuality", "research"]),
    ("master_and_johnson", "马斯特斯和约翰逊", ["sexuality", "research"]),
    ("foreplay", "前戲", ["sexuality", "intimacy"]),
    ("sexual_toy", "性玩具", ["sexuality", "health"]),
    ("self_stimulation", "自慰", ["sexuality", "health"]),
    ("sexual_assault", "性侵犯", ["safety", "consent", "law"]),
    ("open_relationship", "开放式关系", ["relationship", "consent"]),
    ("emotional_affair", "精神出轨", ["relationship", "infidelity"]),
    # 星座 / 玄学：作为天文常识、文化现象与「为什么觉得准」的心理机制
    ("zodiac_constellations", "黄道十二宫", ["astrology", "astronomy", "culture"]),
    ("barnum_effect", "巴纳姆效应", ["bias", "astrology", "psychology"]),
    ("confirmation_bias", "确认偏误", ["bias", "psychology"]),
    ("cold_reading", "冷读术", ["influence", "psychology", "skepticism"]),
    ("forer_effect", "福勒效应", ["bias", "psychology"]),
    ("horoscope", "星座运势", ["astrology", "culture"]),
    ("ascendant_sign", "上升星座", ["astrology", "culture"]),
    ("tarot", "塔罗牌", ["divination", "culture"]),
    ("fortune_telling", "算命", ["divination", "culture"]),
    ("divination", "占卜", ["divination", "culture"]),
    ("bazi", "八字", ["divination", "china", "culture"]),
    ("feng_shui", "风水", ["superstition", "china", "culture"]),
    ("superstition", "迷信", ["belief", "culture"]),
    ("pseudoscience", "伪科学", ["skepticism", "science"]),
    ("supernatural", "超自然", ["belief", "culture"]),
    ("astronomy_of_zodiac", "黄道", ["astronomy", "culture"]),
    ("aries_constellation", "白羊座", ["zodiac", "astronomy"]),
    ("taurus_constellation", "金牛座", ["zodiac", "astronomy"]),
    ("gemini_constellation", "双子座", ["zodiac", "astronomy"]),
    ("cancer_constellation", "巨蟹座", ["zodiac", "astronomy"]),
    ("leo_constellation", "狮子座", ["zodiac", "astronomy"]),
    ("virgo_constellation", "处女座", ["zodiac", "astronomy"]),
    ("libra_constellation", "天秤座", ["zodiac", "astronomy"]),
    ("scorpio_constellation", "天蝎座", ["zodiac", "astronomy"]),
    ("sagittarius_constellation", "射手座", ["zodiac", "astronomy"]),
    ("capricornus_constellation", "摩羯座", ["zodiac", "astronomy"]),
    ("aquarius_constellation", "水瓶座", ["zodiac", "astronomy"]),
    ("pisces_constellation", "双鱼座", ["zodiac", "astronomy"]),
    # Alternates for the titles above that have no standalone article.
    # Removed after the first run: 婚外情/外遇 resolve to one article already
    # covered by EXTRAMARITAL_AFFAIR above, and 上升點 / 威廉·马斯特斯 have no
    # article, so the old prefix-matching search fallback returned 上升2号 (a
    # mountain) and 威廉姆斯车队 (a Formula 1 team).
    ("chinese_astrology", "中國占星學", ["astrology", "china", "culture"]),
    ("chinese_almanac", "黃曆", ["culture", "china", "belief"]),
    # Batch 7: titles verified against the API first (probe), so nothing here
    # depends on the search fallback. Duplicates already in the corpus were left
    # out: 占星术 / 愛情 / 分手 / 精神虐待 / 沟通 / 生殖健康 / 性同意 / 性玩具
    # (and 自恋型人格障碍 / 非暴力沟通, added here by mistake in the first pass).
    ("ziwei_douishu", "紫微斗数", ["astrology", "belief", "china"]),
    ("physiognomy", "面相学", ["belief", "fortune_telling", "culture"]),
    ("sexual_pleasure", "性愉悦", ["sexuality", "health"]),
    ("marital_rape", "婚内强奸", ["consent", "law", "safety"]),
    ("date_rape", "约会强奸", ["consent", "safety", "law"]),
    ("cybersex", "网络性爱", ["sexuality", "online", "safety"]),
]

OFFICIAL = [
    dict(slug="civil_code", title="中华人民共和国民法典", url="https://www.moj.gov.cn/pub/sfbgw/zwgkztzl/2025nianzhuanti/2025mfdxcy/2025mfdxcy_mfdql/202505/t20250507_518708.html", mode="full", source_type="law", license="official_public_document", topics=["law", "marriage", "family", "property"]),
    dict(slug="anti_fraud_law", title="中华人民共和国反电信网络诈骗法", url="http://cpc.people.com.cn/n1/2022/1130/c64387-32577289.html", mode="full", source_type="law", license="official_public_document", topics=["law", "scam", "fraud"]),
    dict(slug="nhc_12356", title="国家卫生健康委关于应用“12356”全国统一心理援助热线电话的通知", url="https://www.nhc.gov.cn/yzygj/c100068/202412/49a1a65386cd4be582d4702fd0926ee8.shtml", alts=["http://dzwjw.dezhou.gov.cn/n67562390/c91722751/content.html"], mode="full", source_type="official_notice", license="official_public_document", topics=["mental_health", "help"]),
    dict(slug="xinhua_scam", title="“完美男友”实为“温柔陷阱” 起底“杀猪盘”套路", url="https://app.xinhuanet.com/news/article.html?articleId=d5af321f620bcb38f8b1746a45e92fc9", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["scam", "money", "online_dating"]),
    dict(slug="cctv_pua", title="如何识别PUA？当发现自己被PUA时又该如何应对？", url="https://news.cctv.com/2021/10/19/ARTIqbbSsnBQ8p0px4WYA76a211019.shtml", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["pua", "abuse", "safety"]),
    dict(slug="shen_yifei", title="“社会学视角下的亲密关系的变迁”专题讲座举办", url="https://shxy.nankai.edu.cn/info/1220/2498.htm", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["relationship", "sociology", "money"]),
    dict(slug="boundaries_zju", title="人际边界的问题（浙江大学心理健康教育与咨询中心）", url="http://www.xlzx.zju.edu.cn/2014/1225/c55639a2236240/page.htm", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["boundaries", "relationship", "communication"]),
    dict(slug="ydl_validation", title="总接不住别人的情绪，是因为我太冷血吗？", url="https://m.ydl.com/jingyan/19441", mode="excerpt", source_type="commercial_psychology", license="copyrighted_excerpt_personal_research", topics=["validation", "empathy"]),
    dict(slug="ky_attachment", title="婚恋情感中的依恋模式：你的爱情安全吗？", url="https://knowyourself.cc/detail?id=smit2lrHT", mode="excerpt", source_type="commercial_psychology", license="copyrighted_excerpt_personal_research", topics=["attachment", "relationship"]),
    dict(slug="zqb_zodiac", title="70.3%受访者称身边喜欢星座文化的人多", url="https://zqb.cyol.com/html/2017-08/10/nw.D110000zgqnb_20170810_4-07.htm", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["zodiac", "culture"]),
    dict(slug="xinhua_mbti", title="“MBTI”成部分大学新生社交“破冰”神器", url="http://www.news.cn/politics/2023-09/18/c_1129868448.htm", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["mbti", "culture"]),
    dict(slug="zqb_aa", title="情侣之间有必要AA制吗？", url="http://news.cyol.com/gb/articles/2021-03/30/content_BYe8eclRa.html", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["money", "relationship", "china"]),
    dict(slug="wuhan_police", title="涉案1.8亿！“完美恋人”全流程", url="https://gaj.wuhan.gov.cn/jmzx/jfts/202506/t20250617_2596634.html", mode="excerpt", source_type="police", license="official_public_document", topics=["scam", "money", "online_dating"]),
    dict(slug="mca_marriage_stats", title="2024年全国婚姻登记数据（结婚登记610.6万对）", url="https://news.cctv.com/2025-02-10/ARTIx9vWgrr6q1QYCmWpL6Ja250210.shtml", alts=["https://news.cnr.cn/native/gd/20250730/t20250730_527291791.shtml"], mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["marriage", "divorce", "statistics"]),
    # 第二批：法律法规、司法解释、官方指南（均已核对可访问）
    dict(slug="anti_dv_law", title="中华人民共和国反家庭暴力法", url="https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=91377", mode="full", source_type="law", license="official_public_document", topics=["law", "abuse", "safety", "family"]),
    dict(slug="guangdong_anti_dv", title="广东省实施《中华人民共和国反家庭暴力法》办法", url="http://www.pwccw.gd.gov.cn/dfzc/content/post_265717.html", mode="full", source_type="local_regulation", license="official_public_document", topics=["law", "abuse", "safety"]),
    dict(slug="women_protection_law", title="中华人民共和国妇女权益保障法（2022年修订）", url="http://politics.people.com.cn/n1/2022/1030/c1001-32554934.html", mode="full", source_type="law", license="official_public_document", topics=["law", "gender", "safety"]),
    dict(slug="marriage_registration_regulation", title="婚姻登记条例（国务院令第804号，2025年修订）", url="https://www.mee.gov.cn/zcwj/gwywj/202504/t20250410_1113983.shtml", alts=["http://www.xinhuanet.com/politics/20250409/8e4e71dae12d43b0817cbc529b40b946/c.html"], mode="full", source_type="administrative_regulation", license="official_public_document", topics=["law", "marriage", "china"]),
    dict(slug="marriage_registration_rules", title="民政部关于印发《婚姻登记工作规范》的通知", url="https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=102674", mode="full", source_type="official_rule", license="official_public_document", topics=["law", "marriage", "china"]),
    dict(slug="marriage_nationwide", title="民政部将施行婚姻登记“全国通办”（赤峰市政府政策解读）", url="https://www.chifeng.gov.cn/zmhd_01/zcwdk/wdkhj/202503/t20250326_2561897.html", mode="full", source_type="official_qa", license="official_public_document", topics=["marriage", "china", "policy"]),
    dict(slug="mental_health_literacy_10", title="心理健康素养十条（2018年版）", url="https://wjw.fujian.gov.cn/jggk/csxx/wsyjbgs/wsyj/201810/t20181018_4684824.htm", mode="full", source_type="official_guide", license="official_public_document", topics=["mental_health", "wellbeing"]),
    dict(slug="marriage_interpretation_1", title="最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释（一）", url="https://www.court.gov.cn/fabu/xiangqing/282071.html", alts=["http://legal.people.com.cn/n1/2021/0104/c42510-31987647.html"], mode="full", source_type="judicial_interpretation", license="official_public_document", topics=["law", "marriage", "property", "family"]),
    dict(slug="family_dispute_cases", title="最高人民法院涉婚姻家庭纠纷典型案例", url="https://www.court.gov.cn/zixun/xiangqing/452761.html", mode="excerpt", source_type="judicial_case", license="official_public_document", topics=["law", "marriage", "money", "family"]),
    # 第三批：高校心理健康教育中心的科普文章与官方媒体专题（均为短摘录）
    dict(slug="people_pleasing_zqb", title="“讨好型人格”：为何学不会勇敢说“不”？", url="http://news.cyol.com/gb/articles/2021-12/25/content_lzmMxuWo8.html", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["people_pleasing", "boundaries", "emotion"]),
    dict(slug="people_pleasing_nbufe", title="「讨好型人格」的五大特征，你有吗？（宁波财经学院心理中心）", url="https://www.nbufe.edu.cn/xl/show.htm?typeid=919&typeid2=919&id=75692", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["people_pleasing", "self_worth", "emotion"]),
    dict(slug="people_pleasing_nufe", title="讨好型人格：如何成为更好的自己（南京财经大学）", url="https://hs.nufe.edu.cn/xsc/2025/0523/c152a23569/pagem.htm", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["people_pleasing", "self_worth", "communication"]),
    dict(slug="people_pleasing_culr", title="【心语聆听】讨好型人格（中国劳动关系学院）", url="https://news.culr.edu.cn/xlzx/xlgw/96a1db330bd741f3bdb26f370b0cb803.htm", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["people_pleasing", "emotion"]),
    dict(slug="intimacy_ecnu", title="亲密关系八周训练营：在人际关系中与自己和他人相处（华东师范大学心理中心）", url="https://xlzx.ecnu.edu.cn/6d/92/c10582a683410/page.htm", mode="excerpt", source_type="university", license="copyrighted_excerpt_personal_research", topics=["relationship", "intimacy", "family_of_origin"]),
    # 第四批（2026-10-26）：成人性健康与婚前保健的官方文件（全文），
    # 以及关于占星/占卜消费与恋爱课程的官方媒体报道（短摘录）。
    dict(slug="hiv_action_plan_2030", title="国务院办公厅关于印发《中国遏制与防治艾滋病规划（2024—2030年）》的通知", url="https://www.ndcpa.gov.cn/jbkzzx/c100030/common/content/content_1866845309482160128.html", mode="full", source_type="official_notice", license="official_public_document", topics=["health", "safer_sex", "policy", "stigma"]),
    dict(slug="hiv_regulation", title="艾滋病防治条例（国务院令第457号，2019年修订）", url="https://xxgk.yczf.gov.cn/xzf/ycwjj/fdzdgknr/fgwj_42006/202012/t20201230_1327978.shtml", alts=["https://www.bjxch.gov.cn/zt/kpzc/xxxq/pnidpv879631.html"], mode="full", source_type="administrative_regulation", license="official_public_document", topics=["health", "safer_sex", "law"]),
    dict(slug="premarital_checkup_norms", title="卫生部关于印发《婚前保健工作规范（修订）》的通知", url="https://ncaids.chinacdc.cn/xxgx/zcwj/201804/t20180419_164349.htm", mode="full", source_type="official_rule", license="official_public_document", topics=["health", "marriage", "reproductive_health"]),
    dict(slug="free_premarital_checkup_shanxi", title="《2022年山西省免费婚前医学检查工作实施方案》的通知", url="http://wjw.shanxi.gov.cn/tzgg/zcwj/202203/t20220311_5330760.shtml", mode="full", source_type="local_official_plan", license="official_public_document", topics=["health", "marriage", "reproductive_health", "policy"]),
    dict(slug="xinhua_fortune_scam", title="热衷占卜不信自己信大师？小心“命数”之中藏骗局", url="http://www.news.cn/politics/2021-11/19/c_1128079308.htm", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["astrology", "scam", "belief"]),
    dict(slug="cyol_metaphysics_youth", title="占星、塔罗……年轻人热衷“玄学”，是减压还是危机？", url="http://news.cyol.com/gb/articles/2021-03/24/content_Vdw55uv7o.html", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["astrology", "culture", "emotion"]),
    dict(slug="cyol_fortune_opinion", title="年轻人爱上算命？情绪出口不该是行动枷锁", url="https://zqb.cyol.com/html/2023-04/12/nw.D110000zgqnb_20230412_7-08.htm", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["astrology", "belief", "psychology"]),
    dict(slug="divination_business", title="算命还是算钱？网络占卜风靡背后有何门道", url="http://www.zgjssw.gov.cn/yaowen/202104/t20210420_7053748.shtml", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["divination", "scam", "money"]),
    dict(slug="divination_myth_bust", title="网络占卜“剧透”人生可信吗（辟谣频道）", url="http://jsnews.jschina.com.cn/piyao/qwfb/202111/t20211102_2884276.shtml", mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["divination", "skepticism", "psychology"]),
    dict(slug="tarot_pig_butchering", title="“塔罗大师”设下“算命杀猪盘”（法治日报案件报道）", url="http://epaper.legaldaily.com.cn/fzrb/content/20251203/Articel06002GN.htm", alts=["https://app.xinhuanet.com/news/article.html?articleId=0dab8f6c1bba31bb9b8febbd777c4698"], mode="excerpt", source_type="official_media", license="copyrighted_excerpt_personal_research", topics=["divination", "scam", "law", "money"]),
    dict(slug="dating_courses_colleges", title="教大学生如何去爱：当恋爱课程走进高校", url="https://www.thepaper.cn/newsDetail_forward_20434533", mode="excerpt", source_type="media_education", license="copyrighted_excerpt_personal_research", topics=["dating", "education", "sexuality"]),
    dict(slug="zodiac_market_data", title="中国人最爱的算命项目，星座和塔罗牌输给了它", url="https://m.thepaper.cn/baijiahao_11568681", mode="excerpt", source_type="media_data", license="copyrighted_excerpt_personal_research", topics=["astrology", "divination", "culture"]),
]

SKILL_REPOS = [
    ("tomwong001", "qingsheng-skill", ["skill", "structure", "policy_filtered"]),
    ("NatalieCao323", "partner-skill", ["skill", "structure", "relationship_metrics"]),
    # Mayuqi-crypto/HowToGetAlongWithGirls is deliberately not listed: it has no
    # licence file (so only a README excerpt could be kept) and that excerpt
    # advertises 废测/废物测试 as a feature, which README section 3 excludes.
]

# Repo plumbing, marketing copy and machine-generated eval logs carry no
# relationship knowledge; they only add noise to the chunks.
SKILL_SKIP_RE = re.compile(
    r"(?:^|/)(?:docs|evals|\.github|node_modules|test|tests|assets|images)/|"
    r"(?:^|/)(?:CHANGELOG|LICENSE|CONTRIBUTING|CODE_OF_CONDUCT|requirements\.txt|"
    r"package\.json|robots\.txt|repo_meta)",
    re.IGNORECASE,
)

# README section 3 excludes manipulation technique. Dating-coach skills usually
# bundle such material in dedicated reference files, so a file is dropped when
# these markers appear repeatedly. Identification-and-self-protection content
# (which names the tactics in order to warn about them) stays well below the
# threshold because it does not repeat the terms per section.
MANIP_MARKERS = re.compile(
    r"服从性测试|compliance test|废物测试|废测|shit test|冷读|cold read|"
    r"推拉|push-?pull|拉扯升温|欲擒故纵|kino|进挪|升高|打压|negging|"
    r"负能量反馈|框架控制|服从度",
    re.IGNORECASE,
)
MANIP_DROP_THRESHOLD = 3

# Translated READMEs repeat the same marketing text in languages the corpus does
# not cover, so only the source-language copies are kept.
SKILL_TRANSLATION_RE = re.compile(r"^README_(?!EN\b)[A-Z]{2,3}\.md$")

# Files that sit below the marker threshold but still teach scripted lines or
# read a partner's resistance as consent (examples-library.md's kino passage).
SKILL_MANUAL_DROP = {
    "qingsheng-skill": {"skill/references/examples-library.md"},
}

# README badges and embedded SVG data URIs would otherwise be chunked as text.
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"</?(?:[a-zA-Z][a-zA-Z0-9]*)\b[^>]{0,4000}>")
LONG_TOKEN_RE = re.compile(r"\S{200,}")


def clean_skill_markdown(text: str) -> str:
    text = MD_IMAGE_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    text = LONG_TOKEN_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", text)

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
})

# A few government sites reject the research User-Agent with HTTP 412; retry
# those with a normal browser fingerprint before giving up.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.gov.cn/",
}


def get_html(url: str, alts: list[str] | None = None) -> tuple[str, bytes] | None:
    """Fetch a page, trying alternate mirrors and a browser fingerprint.

    Returns (final_url, content) or None when every attempt failed.
    """
    for candidate in [url, *(alts or [])]:
        for headers in (None, BROWSER_HEADERS):
            try:
                resp = session.get(candidate, timeout=45, headers=headers or {})
                if resp.status_code == 200 and resp.content:
                    return candidate, resp.content
                log.info("http %s for %s", resp.status_code, candidate)
            except Exception as exc:
                log.info("fetch error %s: %s", candidate, exc)
            time.sleep(0.5)
    return None


def clean_lines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def html_text(content: bytes) -> tuple[str, str]:
    soup = BeautifulSoup(content, "lxml")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"]):
        tag.decompose()
    node = None
    for sel in (".v_news_content", ".wp_articlecontent", ".trs_editor_view", "#printContent",
                "article", "main", ".article-content", ".article_content", ".TRS_Editor",
                ".content", "#content", ".view", ".post-content"):
        candidate = soup.select_one(sel)
        if candidate is not None and len(clean_lines(candidate.get_text("\n"))) > 300:
            node = candidate
            break
    if node is None:
        node = soup.body or soup
    return title, clean_lines(node.get_text("\n"))


def save_record(record: dict) -> None:
    path = RECORDS / f"{record['doc_id']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


WIKI_API = "https://zh.wikipedia.org/w/api.php"


def wiki_request(params: dict, label: str) -> requests.Response | None:
    for attempt in range(5):
        try:
            resp = session.get(WIKI_API, params=params, timeout=45)
        except Exception as exc:
            log.warning("wiki error %s: %s", label, exc)
            time.sleep(3 + attempt * 4)
            continue
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After") or 10) + attempt * 5
            log.warning("wiki 429 %s, waiting %ss", label, wait)
            time.sleep(wait)
            continue
        if resp.ok:
            return resp
        log.warning("wiki http %s for %s", resp.status_code, label)
        time.sleep(2 + attempt * 3)
    return None


def wiki_page(title: str) -> tuple[str, dict] | None:
    """Return (requested_title, page) using variant conversion."""
    resp = wiki_request(
        {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": "1",
            "inprop": "url",
            "redirects": "1",
            "converttitles": "1",
            "format": "json",
            "formatversion": "2",
            "titles": title,
        },
        title,
    )
    if resp is None:
        return None
    pages = (resp.json().get("query") or {}).get("pages") or []
    if not pages:
        return None
    page = pages[0]
    if page.get("missing") or page.get("invalid"):
        return None
    return title, page


def _wiki_key(text: str) -> str:
    """Comparison key: whitespace and disambiguation suffix removed."""
    stripped = re.sub(r"\s+", "", text)
    return re.sub(r"[（(][^（()]*[)）]$", "", stripped)


def wiki_search_title(title: str) -> str | None:
    """Fallback: only accept a search hit that is the same article name.

    Prefix matching is worse than no hit at all: "威廉·马斯特斯" once returned
    "威廉姆斯车队" and "上升點" returned "上升2号". Whole-name equality keeps the
    fallback useful for spelling variants without inventing content.
    """
    resp = wiki_request(
        {
            "action": "query",
            "list": "search",
            "srsearch": title,
            "srlimit": "3",
            "format": "json",
            "formatversion": "2",
        },
        f"search:{title}",
    )
    if resp is None:
        return None
    want = _wiki_key(title)
    for hit in (resp.json().get("query") or {}).get("search") or []:
        cand = hit.get("title") or ""
        if cand and _wiki_key(cand) == want:
            return cand
    return None


def write_wiki(slug: str, requested: str, page: dict, topics: list[str]) -> int:
    """Write raw JSON, attributed text and the manifest record. Returns chars."""
    final_title = page.get("title", requested)
    url = page.get("fullurl") or f"https://zh.wikipedia.org/wiki/{quote(final_title)}"
    extract = clean_lines(page.get("extract") or "")
    raw_path = RAW_WIKI / f"{slug}.json"
    raw_path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
    header = "\n".join([
        f"TITLE: {final_title}",
        "SOURCE: Chinese Wikipedia",
        f"URL: {url}",
        "LICENSE: CC BY-SA 4.0",
        "LICENSE_URL: https://creativecommons.org/licenses/by-sa/4.0/",
        "ATTRIBUTION: Text adapted from the Chinese Wikipedia article named above,",
        "  available under the Creative Commons Attribution-ShareAlike 4.0 license.",
        f"RETRIEVED: {datetime.now(timezone.utc).isoformat()}",
        f"TOPICS: {', '.join(topics)}",
        "",
        "---",
        "",
        extract,
    ])
    text_path = TEXT_WIKI / f"{slug}.txt"
    text_path.write_text(header, encoding="utf-8")
    record = {
        "doc_id": f"wiki_{slug}",
        "source": "zh_wikipedia",
        "source_type": "encyclopedia",
        "title": final_title,
        "requested_title": requested,
        "url": url,
        "language": "zh",
        "license": "CC BY-SA 4.0",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "attribution": f"Chinese Wikipedia: {final_title}",
        "topics": topics,
        "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_bytes": raw_path.stat().st_size,
        "text_chars": len(header),
        "text_sha256": hashlib.sha256(header.encode("utf-8")).hexdigest(),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    save_record(record)
    return len(header)


def fetch_wikipedia() -> None:
    """Fetch one page per request.

    TextExtracts only returns a full plain-text extract for a single title even
    with exlimit=max, so batching cannot be used here; pacing is what keeps the
    429s manageable.
    """
    saved = missing = 0
    pending = [
        (slug, title, topics)
        for slug, title, topics in WIKI
        if not (TEXT_WIKI / f"{slug}.txt").exists()
    ]
    skipped = len(WIKI) - len(pending)
    log.info("wikipedia pending=%d already_saved=%d", len(pending), skipped)
    for slug, title, topics in pending:
        found = wiki_page(title)
        page = found[1] if found else None
        extract = clean_lines((page or {}).get("extract") or "")
        if page is None or len(extract) < 200:
            alt = wiki_search_title(title)
            if alt and alt != title:
                log.info("wiki redirect-by-search: %s -> %s", title, alt)
                found = wiki_page(alt)
                if found:
                    page = found[1]
                    extract = clean_lines(page.get("extract") or "")
        if page is None:
            missing += 1
            log.warning("wiki missing: %s", title)
            time.sleep(1.0)
            continue
        if len(extract) < 200:
            missing += 1
            log.warning("wiki extract too short: %s (%s chars)", title, len(extract))
            time.sleep(1.0)
            continue
        try:
            chars = write_wiki(slug, title, page, topics)
            saved += 1
            log.info("wiki saved: %s (%s chars)", page.get("title", title), chars)
        except Exception as exc:
            log.warning("wiki write failed %s: %s", title, exc)
        time.sleep(3.0)
    log.info("wikipedia done: saved=%d missing=%d skipped_existing=%d", saved, missing, skipped)


def fetch_official() -> None:
    for item in OFFICIAL:
        if (TEXT_ZH / f"{item['slug']}.txt").exists():
            continue
        got = get_html(item["url"], item.get("alts"))
        if got is None:
            log.warning("official unreachable: %s", item["slug"])
            continue
        final_url, content = got
        try:
            raw_path = RAW_ZH / f"{item['slug']}.html"
            raw_path.write_bytes(content)
            page_title, text = html_text(content)
            if len(text) < 100:
                log.warning("official text too short: %s (%s chars)", item["slug"], len(text))
                continue
            if item["mode"] == "excerpt":
                text = text[:1800]
                note = "\n\n[说明] 这是个人研究用的短摘录，完整内容请访问来源链接；版权归原权利人。"
            else:
                note = "\n\n[说明] 官方公开文件/公告，全文保存用于个人研究。"
            header = "\n".join([
                f"TITLE: {item['title']}",
                f"PAGE_TITLE: {page_title}",
                f"SOURCE: {item['source_type']}",
                f"URL: {final_url}",
                f"LICENSE: {item['license']}",
                f"RETRIEVED: {datetime.now(timezone.utc).isoformat()}",
                f"TOPICS: {', '.join(item['topics'])}",
                f"MODE: {item['mode']}",
                "",
                "---",
                "",
                text + note,
            ])
            text_path = TEXT_ZH / f"{item['slug']}.txt"
            text_path.write_text(header, encoding="utf-8")
            record = {
                "doc_id": f"zh_{item['slug']}",
                "source": "zh_official",
                "source_type": item["source_type"],
                "title": item["title"],
                "page_title": page_title,
                "url": final_url,
                "requested_url": item["url"],
                "language": "zh",
                "license": item["license"],
                "license_url": "",
                "topics": item["topics"],
                "excerpt_only": item["mode"] == "excerpt",
                "raw_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_bytes": raw_path.stat().st_size,
                "text_chars": len(header),
                "text_sha256": hashlib.sha256(header.encode("utf-8")).hexdigest(),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            save_record(record)
            log.info("zh saved: %s mode=%s chars=%s", item["title"][:50], item["mode"], len(header))
            time.sleep(0.3)
        except Exception as exc:
            log.warning("official failed %s: %s", item["slug"], exc)


def fetch_github_skill(owner: str, repo: str, topics: list[str]) -> None:
    api = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        meta_resp = session.get(api, timeout=30)
        meta_resp.raise_for_status()
        meta = meta_resp.json()
        spdx = ((meta.get("license") or {}).get("spdx_id") or "").strip()
        branch = meta.get("default_branch") or "main"
        repo_dir = RAW_SKILLS / repo
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "repo_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tree_resp = session.get(f"{api}/git/trees/{branch}?recursive=1", timeout=30)
        tree = tree_resp.json().get("tree", []) if tree_resp.ok else []
        md_paths = [x["path"] for x in tree if x.get("type") == "blob" and x["path"].lower().endswith((".md", ".txt")) and x.get("size", 0) < 250_000]
        if not md_paths:
            md_paths = [p for p in ("README.md", "SKILL.md") if p]
        permitted = spdx in {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0"}
        if not permitted:
            preferred = [p for p in md_paths if p.lower() in {"readme.md", "skill.md", "readme.txt"} or p.lower().startswith(("readme", "skill"))]
            md_paths = preferred or md_paths[:2]
        kept: list[tuple[str, str]] = []
        dropped_policy: list[str] = []
        skipped_plumbing = 0
        manual_drop = SKILL_MANUAL_DROP.get(repo, set())
        for path in md_paths[:60]:
            # "plumbing" here also covers boilerplate and duplicate translations.
            if (SKILL_SKIP_RE.search(path)
                    or SKILL_TRANSLATION_RE.match(path.rsplit("/", 1)[-1])
                    or path in manual_drop):
                skipped_plumbing += 1
                continue
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            r = session.get(raw_url, timeout=30)
            if not r.ok or not r.content:
                continue
            text = clean_skill_markdown(r.content.decode("utf-8", errors="replace").replace("\r\n", "\n"))
            if not permitted:
                text = text[:1800] + "\n\n[说明] 该仓库许可证不明确，仅保存短摘录用于研究。"
            if len(MANIP_MARKERS.findall(text)) >= MANIP_DROP_THRESHOLD:
                dropped_policy.append(path)
                continue
            (repo_dir / path.replace("/", "__")).write_text(text, encoding="utf-8")
            kept.append((path, text))
        if not kept:
            log.info("skill skipped %s/%s: nothing survives the filters", owner, repo)
            return
        if meta.get("license"):
            (repo_dir / "LICENSE.json").write_text(json.dumps(meta["license"], ensure_ascii=False, indent=2), encoding="utf-8")
        # Full text only for permissive licenses; otherwise keep a short excerpt.
        parts = [
            f"TITLE: {owner}/{repo}",
            f"URL: {meta.get('html_url', '')}",
            f"DESCRIPTION: {meta.get('description', '')}",
            f"LICENSE: {spdx or 'no_license_found'}",
            f"LICENSE_URL: {(meta.get('license') or {}).get('url', '')}",
            f"TOPICS: {', '.join(topics)}",
            f"POLICY_DROPPED: {', '.join(dropped_policy) or 'none'}",
            f"RETRIEVED: {datetime.now(timezone.utc).isoformat()}",
            "",
            "---",
            "",
        ]
        for path, text in kept:
            parts.append(f"FILE: {path}\n{text}\n")
        out = TEXT_SKILLS / f"{repo}.md"
        body = "\n".join(parts)
        out.write_text(body, encoding="utf-8")
        cjk = sum(1 for c in body if "\u4e00" <= c <= "\u9fff")
        record = {
            "doc_id": f"skill_{repo}",
            "source": "github_skill",
            "source_type": "ai_skill",
            "title": f"{owner}/{repo}",
            "repo": f"{owner}/{repo}",
            "url": meta.get("html_url", ""),
            "language": "zh" if cjk > len(body) * 0.05 else "en",
            "license": spdx or "no_license_found",
            "license_url": (meta.get("license") or {}).get("url", ""),
            "topics": topics,
            "excerpt_only": not permitted,
            "raw_path": str(repo_dir.relative_to(ROOT)).replace("\\", "/"),
            "text_path": str(out.relative_to(ROOT)).replace("\\", "/"),
            "raw_bytes": sum(len(t.encode("utf-8")) for _, t in kept),
            "text_chars": len(body),
            "policy_dropped_files": dropped_policy,
            "skipped_plumbing_files": skipped_plumbing,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        save_record(record)
        log.info("skill saved: %s license=%s kept=%s policy_dropped=%s plumbing=%s",
                 repo, spdx or "none", len(kept), len(dropped_policy), skipped_plumbing)
        for dropped in dropped_policy:
            log.info("  policy drop: %s", dropped)
    except Exception as exc:
        log.warning("skill failed %s/%s: %s", owner, repo, exc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "wiki", "official", "skills"], default="all")
    args = ap.parse_args()
    if args.only in {"all", "wiki"}:
        log.info("fetching %s wikipedia pages", len(WIKI))
        fetch_wikipedia()
    if args.only in {"all", "official"}:
        log.info("fetching %s Chinese public/media sources", len(OFFICIAL))
        fetch_official()
    if args.only in {"all", "skills"}:
        log.info("fetching %s GitHub skills", len(SKILL_REPOS))
        for owner, repo, topics in SKILL_REPOS:
            fetch_github_skill(owner, repo, topics)
    log.info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
