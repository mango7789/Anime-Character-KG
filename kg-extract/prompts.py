
EXTRACTION_PROMPT = '''你是一个知识图谱构建助手，任务是从给定文本（均为萌娘百科爬取的内容）中抽取【结构化知识三元组】。

【一、知识 Schema】
你必须严格遵循以下 schema，只能使用其中定义的实体类型与关系名称，不得自行创造新类型或关系。

{schema}

【二、抽取规则（非常重要）】

1. 只抽取【文本中明确出现】的事实，不要推断、补全或常识扩展。
2. 每个三元组必须满足：
   - head 和 tail 都是明确的实体或属性
   - relation 必须严格匹配 schema 中定义的关系名
3. Between_Character 中的关系：
   - head_type 和 tail_type 必须都是 "Character"
4. 如果一段文本中包含多个关系字段（如“父亲：… 母亲：…”）：
   - 必须按字段分别抽取
   - 不允许把同一行中不同字段的实体混在同一个关系下
5. Wiki 标记说明：
   - [[实体名]] 表示一个实体
   - 如果同一字段中出现多个实体，分别生成多条三元组
6. 不要把：
   - 关系名
   - 注释性文字
   - 模板说明
   当作实体
7. 如果 tail 是人名但表示虚构角色 → 类型为 Character
   如果 tail 是现实中的声优 / 作者 → 类型为 Person
8. 声优只需抽取日本的，忽略国语配音的包括台湾、香港、大陆等

【三、输出格式】

你必须输出一个 JSON 数组，每个元素是一个三元组对象，格式如下：

{
  "head": "实体名",
  "relation": "关系名（来自 schema）",
  "tail": "实体名或属性值",
  "head_type": "实体类型",
  "tail_type": "实体类型或属性类型",
  "source": "MoegirlWiki",
  "raw": "用于抽取该三元组的原始文本片段"
}

- 输出必须是【合法 JSON】
- 不要输出任何解释性文字
- 如果没有可抽取的三元组，输出空数组 []

【四、示例】

主实体：
利威尔·阿克曼

输入文本：
{
  "image": "Levicut.jpg",
  "本名": "{{lj|リヴァイ・アッカーマン}}<br />(Levi Ackerman)",
  "别号": "{{lj|人類最強の兵士}}<br />兵长、<del>死矮子、一米六、粒微矮</del>、小陀螺、<del>小豆丁</del>、里维·阿加曼",
  "瞳色": "灰",
  "发色": "黑",
  "身高": "160",
  "体重": "65",
  "生日": "12月25日",
  "星座": "{{Astrology|12|25}}",
  "年龄": "34-38",
  "血型": "A",
  "三围": "B:80 W:62.4 H:80",
  "多位声优": "{{cate|[[神谷浩史]]（日本）<br />[[黄启昌]]（中国香港·TVB）<br />[[刘鹏杰]]（中国台湾）|神谷浩史配音角色|黄启昌配音角色|刘杰配音角色}}",
  "萌点": "[[毒舌]]、[[高冷]]、[[傲娇]]、[[披风]]、[[死鱼眼]]、[[三白眼]]、[[洁癖]]、[[刀剑]]、[[最強]]、鬥神、[[上司]]、[[童颜]]{{黑幕|、[[独眼]]}}",
  "出身地区": "地下城",
  "活动范围": "墙外",
  "所属团体": "[[调查兵团]]<br>[[调查兵团特别作战小组]]<br>（利威尔班）",
  "个人状态": "存活{{黑幕|（已成残疾人）}}",
  "相关人士": "上司：[[艾尔文·史密斯]]<br />母亲：[[库谢尔·阿克曼]]<br />舅舅：[[凯尼·阿克曼]]<br />友人：[[伊莎贝尔·玛格诺]]、[[法兰·恰奇]]、[[韩吉·佐耶]]\n{{黑幕|女人缘：[[佩托拉·拉尔]]}}"
}

输出：
[
  {
      "head": "利威尔·阿克曼",
      "relation": "AppearsIn",
      "tail": "进击的巨人",
      "head_type": "Character",
      "tail_type": "Work",
      "source": "MoegirlWiki"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "VoiceBy",
      "tail": "神谷浩史",
      "head_type": "Character",
      "tail_type": "Person",
      "source": "MoegirlWiki",
      "raw": "{{cate|[[神谷浩史]]（日本）"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasSuperior",
      "tail": "艾尔文·史密斯",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "上司：[[艾尔文·史密斯]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasMother",
      "tail": "库谢尔·阿克曼",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "母亲：[[库谢尔·阿克曼]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasUncle",
      "tail": "凯尼·阿克曼",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "舅舅：[[凯尼·阿克曼]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasFriend",
      "tail": "伊莎贝尔·玛格诺",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "友人：[[伊莎贝尔·玛格诺]]、[[法兰·恰奇]]、[[韩吉·佐耶]]\n女人缘：[[佩托拉·拉尔]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasFriend",
      "tail": "法兰·恰奇",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "友人：[[伊莎贝尔·玛格诺]]、[[法兰·恰奇]]、[[韩吉·佐耶]]\n女人缘：[[佩托拉·拉尔]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HasFriend",
      "tail": "韩吉·佐耶",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "友人：[[伊莎贝尔·玛格诺]]、[[法兰·恰奇]]、[[韩吉·佐耶]]\n女人缘：[[佩托拉·拉尔]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "女人缘",
      "tail": "佩托拉·拉尔",
      "head_type": "Character",
      "tail_type": "Character",
      "source": "MoegirlWiki",
      "raw": "友人：[[伊莎贝尔·玛格诺]]、[[法兰·恰奇]]、[[韩吉·佐耶]]\n女人缘：[[佩托拉·拉尔]]"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Alias",
      "tail": "人類最強の兵士",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "{{lj|人類最強の兵士}}<br />兵长、<del>死矮子、一米六、粒微矮</del>、小陀螺、<del>小豆丁</del>、里维·阿加曼"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Alias",
      "tail": "兵长",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "{{lj|人類最強の兵士}}<br />兵长、<del>死矮子、一米六、粒微矮</del>、小陀螺、<del>小豆丁</del>、里维·阿加曼"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Alias",
      "tail": "小陀螺",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "{{lj|人類最強の兵士}}<br />兵长、<del>死矮子、一米六、粒微矮</del>、小陀螺、<del>小豆丁</del>、里维·阿加曼"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Alias",
      "tail": "里维·阿加曼",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "{{lj|人類最強の兵士}}<br />兵长、<del>死矮子、一米六、粒微矮</del>、小陀螺、<del>小豆丁</del>、里维·阿加曼"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "BirthDate",
      "tail": "12月25日",
      "head_type": "Character",
      "tail_type": "Time",
      "source": "MoegirlWiki",
      "raw": "12月25日"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Height",
      "tail": "160",
      "head_type": "Character",
      "tail_type": "Numeric",
      "source": "MoegirlWiki",
      "raw": "160"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Weight",
      "tail": "65",
      "head_type": "Character",
      "tail_type": "Numeric",
      "source": "MoegirlWiki",
      "raw": "65"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "EyeColor",
      "tail": "灰",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "灰"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "HairColor",
      "tail": "黑",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "黑"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "Origin",
      "tail": "地下城",
      "head_type": "Character",
      "tail_type": "Location",
      "source": "MoegirlWiki",
      "raw": "地下城"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "ActiveArea",
      "tail": "墙外",
      "head_type": "Character",
      "tail_type": "Location",
      "source": "MoegirlWiki",
      "raw": "墙外"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "LivingStatus",
      "tail": "存活（已成残疾人）",
      "head_type": "Character",
      "tail_type": "Literal",
      "source": "MoegirlWiki",
      "raw": "存活{{黑幕|（已成残疾人）}}"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "MemberOf",
      "tail": "调查兵团",
      "head_type": "Character",
      "tail_type": "Group",
      "source": "MoegirlWiki",
      "raw": "[[调查兵团]]<br>[[调查兵团特别作战小组]]<br>（利威尔班）"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "MemberOf",
      "tail": "调查兵团特别作战小组",
      "head_type": "Character",
      "tail_type": "Group",
      "source": "MoegirlWiki",
      "raw": "[[调查兵团]]<br>[[调查兵团特别作战小组]]<br>（利威尔班）"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "MemberOf",
      "tail": "利威尔班",
      "head_type": "Character",
      "tail_type": "Group",
      "source": "MoegirlWiki",
      "raw": "[[调查兵团]]<br>[[调查兵团特别作战小组]]<br>（利威尔班）"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "CharacterTag",
      "tail": "毒舌",
      "head_type": "Character",
      "tail_type": "Tag",
      "source": "MoegirlWiki",
      "raw": "[[毒舌]]、[[高冷]]、[[傲娇]]、[[披风]]、[[死鱼眼]]、[[三白眼]]、[[洁癖]]、[[刀剑]]、[[最強]]、鬥神、[[上司]]、[[童颜]]{{黑幕|、[[独眼]]}}"
    },
    {
      "head": "利威尔·阿克曼",
      "relation": "CharacterTag",
      "tail": "高冷",
      "head_type": "Character",
      "tail_type": "Tag",
      "source": "MoegirlWiki",
      "raw": "[[毒舌]]、[[高冷]]、[[傲娇]]、[[披风]]、[[死鱼眼]]、[[三白眼]]、[[洁癖]]、[[刀剑]]、[[最強]]、鬥神、[[上司]]、[[童颜]]{{黑幕|、[[独眼]]}}"
    },
    ...
]

【五、当前任务】

- 已知当前页面的主实体是一个 Character
- 主实体名称会在输入中显式给出
- 给定一段文本（可能是 JSON 字符串或 Wiki 原文）

请严格按照上述规则，抽取所有符合 schema 的知识三元组，并以 JSON 数组形式输出。


'''
