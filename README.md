## Anime Characters Knowledge Graph

### 数据爬取与知识抽取
```
cd kg-extract
## 抽取动画信息
python moegirl_anime.py
## 抽取角色信息（按动画归类）
python moegirl_anime_character.py
```


### 前端

```
cd kg-ui
npm i react-force-graph-2d
npm run dev
```

### neo4j

```
docker pull neo4j:5
docker run \
  --runtime=runc \
  --name neo4j-anime \
  -p 7474:7474 \
  -p 7688:7687 \
  -e NEO4J_AUTH=neo4j/anime123 \
  -d neo4j:5
```

也可以直接通过 http://10.176.40.144:7474/browser/ 访问，需要在校园网环境下，账号密码是 neo4j 和 anime123

### 后端

配置 python 环境
```
conda env create -f environment.yml
conda activate Anime
```

启动后端服务
```
cd kg-backend
python run.py
```

### 问答
cd kg-chat
python anime_kgqa.py
会对用户输入的prompt进行实体识别和意图识别，把识别出的字段按照规则在知识图谱中搜索，最后给大模型组织语言
