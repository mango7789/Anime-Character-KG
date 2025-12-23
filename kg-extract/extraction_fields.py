import zhconv
import re
# 繁体字 --> 简体字
def traditional_to_simplified(traditional_text):
    simplified_text = zhconv.convert(traditional_text, 'zh-hans')
    return simplified_text

FIELD_TO_RELATION_ANIME = {
    "作者": {
        "relation": "OriginalAuthor",
        "type": "Person"
    },
    "原作": {
        "relation": "OriginalAuthor",
        "type": "Person"
    },
    "出版社": {
        "relation": "Publisher",
        "type": "Organization"
    },
    "发表期间": {
        "relation": "PublicationPeriod",
        "type": "Time"
    },
    "制作公司": {
        "relation": "ProductionCompany",
        "type": "Organization"
    },
    "监督": {
        "relation": "ChiefDirector",
        "type": "Person"
    },
    "系列构成": {
        "relation": "SeriesComposition",
        "type": "Person"
    },
    "角色设计": {
        "relation": "CharacterDesigner",
        "type": "Person"
    },
    "音乐": {
        "relation": "Music",
        "type": "Person"
    },
    "首播时间": {
        "relation": "FirstReleaseDate",
        "type": "Time"
    }
}

FIELD_TO_RELATION_ROLE = {
    # ===== Basic Attributes =====
    "别号": {
        "relation": "Alias",
        "type": "Literal"
    },
    "性别": {
        "relation": "Gender",
        "type": "Literal"
    },
    "生日": {
        "relation": "BirthDate",
        "type": "Time"
    },
    "身高": {
        "relation": "Height",
        "type": "Numeric"
    },
    "体重": {
        "relation": "Weight",
        "type": "Numeric"
    },
    "瞳色": {
        "relation": "EyeColor",
        "type": "Literal"
    },
    "发色": {
        "relation": "HairColor",
        "type": "Literal"
    },
    "出身地区": {
        "relation": "Origin",
        "type": "Location"
    },
    "活动范围": {
        "relation": "ActiveArea",
        "type": "Location"
    },
    "个人状态": {
        "relation": "LivingStatus",
        "type": "Literal"
    },

    # ===== Group / Affiliation =====
    "所属团体": {
        "relation": "MemberOf",
        "type": "Group"
    },
    "担当": {
        "relation": "HasPosition",
        "type": "Literal",
    },

    # ===== Tags =====
    "萌点": {
        "relation": "CharacterTag",
        "type": "Tag"
    }
}

FIELD_RELATION_BETWEEN_ROLES = {
    # ===== 直系血缘 =====
    "HasParent": ["父母", "双亲"],
    "HasFather": ["父亲", "父", "爸爸", "爹", "生父"],
    "HasMother": ["母亲", "母", "妈妈", "娘", "生母"],

    "HasSon": ["儿子"],
    "HasDaughter": ["女儿"],
    "HasChild": ["子女", "孩子"],

    # ===== 收养 / 法理血缘 =====
    "HasAdoptiveParent": ["养父母"],
    "HasAdoptiveFather": ["养父"],
    "HasAdoptiveMother": ["养母"],
    "HasAdoptiveSon": ["养子"],
    "HasAdoptiveDaughter": ["养女"],

    # ===== 祖辈 / 世代 =====
    "HasGrandParent": ["祖父母", "公婆"],
    "HasGrandFather": ["祖父", "爷爷", "外公", "爷"],
    "HasGrandMother": ["祖母", "奶奶", "外婆", "奶"],

    "HasAncestor": ["祖先"],
    "HasDescendant": ["后代"],

    # ===== 兄弟姐妹 =====
    "HasOlderBrother": ["哥哥", "兄长", "大哥", "兄"],
    "HasYoungerBrother": ["弟弟", "弟"],
    "HasOlderSister": ["姐姐", "姊姊", "姊", "姐"],
    "HasYoungerSister": ["妹妹", "妹"],

    # ===== 旁系亲属 =====
    "HasUncle": ["叔叔", "伯父", "舅舅", "舅子"],
    "HasAunt": ["阿姨", "姑姑", "舅妈"],
    "HasCousin": ["堂兄", "堂姐", "堂妹", "堂弟", "表兄", "表姐", "表妹", "表弟"],
    "HasRelative": ["亲戚", "远房亲戚", "远亲"],

    # ===== 情感纽带 =====
    "HasChildhoodFriend": ["青梅竹马", "青梅", "幼驯染", "儿时玩伴", "儿时友人"],
    "HasFriend": ["朋友", "好友", "友人", "玩伴"],
    "HasBestFriend": ["挚友", "至交"],
    "HasCompanion": ["同伴", "伙伴", "搭档"],
    "HasComrade": ["战友", "并肩作战", "同袍", "战场伙伴"],

    # ===== 恋爱 / 婚姻 =====
    "HasLover": ["恋人", "爱人", "伴侣", "恋情", "对象", "爱慕", "喜欢的人", "男友", "女友"],
    "HasSpouse": ["丈夫", "妻子", "配偶", "老公", "老婆", "妻"],
    "HasExLover": ["前女友", "前男友", "前任"],
    # ===== 恋爱衍生 / fandom =====
    "HasRomanticRival": ["情敌"],
    "IsCoupledWith": ["CP", "cp", "官配"],

    # ===== 教育 / 同辈 =====
    "HasPeer": ["同期", "同级", "校友", "同学", "同班", "同门"],
    "HasSenior": ["学长", "学姐", "前辈"],
    "HasJunior": ["学弟", "学妹", "后辈"],

    # ===== 师承 =====
    "HasMentor": ["导师", "指导老师", "师父", "师傅", "老师", "教师", "班主任"],
    "HasStudent": ["学生", "弟子", "徒弟"],

    # ===== 职场 / 权力 =====
    "HasSuperior": ["上司", "指挥官", "队长", "长官"],
    "HasSubordinate": ["部下", "下属", "属下", "副官", "助手"],
    "HasColleague": ["同事", "同僚"],

    # ===== 主仆 / 契约 =====
    "HasMaster": ["主人", "主君", "君主", "雇主", "领主", "大小姐", "少爷", "主上", "主公"],
    "HasServant": ["仆人", "仆从", "侍从", "随从", "家臣", "女仆", "男仆", "执事", "从者"],
    "HasContractWith": ["契约"],

    # ===== 超自然 / 状态 =====
    "IsPossessedBy": ["被附身", "肉体占据"],

    # ===== 对立 =====
    "HasEnemy": ["敌人", "宿敌", "仇敌", "敌对", "仇人", "死敌", "敌"],
    "HasRival": ["对手", "竞争对手", "对立"],
    # ===== 道德 / 情感评价 =====
    "HasBenefactor": ["恩人"],
    # ===== 崇拜 / 单向 =====
    "IsFanOf": ["粉丝", "迷妹", "迷弟", "偶像"],
}

def infer_role_relation(raw_relation: str):
    """
    输入萌百原始关系词，如：
    - '异母兄'
    - '养父'
    - '青梅竹马'
    返回：
    - schema_relation (str)
    """
    raw_relation = traditional_to_simplified(raw_relation)
    # 1. 精确匹配
    relation_dict = {}
    for relation, keywords in FIELD_RELATION_BETWEEN_ROLES.items():
        for kw in keywords:
            if kw in raw_relation:
                relation_dict[kw] = relation
    if raw_relation in relation_dict:
        return relation_dict[raw_relation]
    
    raw_relation = raw_relation.split('的')[-1]
    if raw_relation in relation_dict:
        return relation_dict[raw_relation]

    # 2. 模糊匹配
    for k in sorted(relation_dict.keys(), key=lambda x: -len(x)):
        if k in raw_relation:
            return relation_dict[k]
    # 3. 完全无法判断
    return raw_relation

