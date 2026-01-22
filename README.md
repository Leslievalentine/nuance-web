# Nuance Engine (NuanceLog)

> **Data-Driven Lexical Analysis for Language Learners**
>
> *"在这个过程中，最重要的或许不是写出了一个粗糙的项目，而是锻炼了自己认识一个好产品的能力，以及意识到——技术变革正在让普通人拥有平等将想法落地的权利。"*

## 📝 背景与思考 (Background & Philosophy)

**从 HTML 到全栈开发的跨越**

这个项目的起点非常简单。起初只是希望借助 AI 写一个简单的 HTML 前端页面，用于展示我对英语单词的一些想法。

作为一个英语专业的学生，在学习中发现了一个普遍的痛点：传统的词典往往只提供静态的释义，却很难量化单词在真实语境中的**微妙差异（Nuance）**。例如，同义词 `think` 和 `reckon`，在词典中可能都被解释为“认为”，但在 BNC（书面语料库）和 MASC（口语语料库）中的生存状态却截然不同。

在与 AI 协作的过程中，我意识到仅仅做一个静态网页不足以承载这个想法。技术的边界在 AI 的辅助下被极大地拓宽了。我开始尝试以一个完全“小白”的身份，去构建后端、设计数据库、处理复杂的语料数据。

**产品思维的实践**

Nuance Engine 的代码是粗糙的，架构也是不成熟的。但对于我而言，这个项目的核心价值在于它是一次**产品思维的实践**。

它让我从单纯的“语言学习者”转变为“工具创造者”。我开始思考：
* 如何通过数据可视化（双雷达图）来解决“语感不可见”的问题？
* 如何通过交互设计（三段式布局）来降低信息的获取成本？
* 如何利用技术（NLP）去验证语言学的假设？

## 🧩 核心功能 (Core Features)

尽管这是一个 MVP（最小可行性产品），但它通过数据驱动的方式，实现了以下核心功能：

### 1. 语域双图 (Dual Corpus Radar)
为了客观展示单词的生存环境，我们摒弃了单一维度的分析。
* **Written Profile (BNC)**：基于 BNC 语料，动态计算该词在学术、文学等书面语域的累积占比。
* **Spoken Profile (MASC)**：基于 MASC 语料，展示该词在社交媒体、对话等非正式场合的分布。
* *设计考量：通过左右分图，解决了不同语料库标签体系不兼容的问题，直观呈现单词的“性格”。*

### 2. 构式提取引擎 (Syntactic Pattern Engine)
单词的意义往往由其搭配决定。
* **Pattern Mode**：针对动词，自动提取句法结构（如 `V + that clause`）。
* **Linear Mode**：针对名词/形容词，提取高频搭配（如 `Adj + N`）。
* 每条搭配均附带经过筛选的真实语料库例句，而非人工编造的句子。

### 3. 沉浸式 UI 体验
参考了专业词典（如 Eudic）的交互逻辑。
* **布局**：采用“拼写-释义-辨析”的三段式垂直布局。
* **视觉**：使用 Tailwind CSS 进行了细致的排版，试图在网页端还原纸质书的阅读体验。

## 🚧 开发历程与技术收获 (Dev Journey & Learnings)

作为一个编程新手，这个项目的诞生经历了无数次试错。在与 AI 的多轮对话中，我终于完成了代码，也补上了计算机科学中宝贵的实践课：

1.  **数据工程的启蒙**：
    从最初面对几百兆文本文件的束手无策，到学会使用 Python 编写脚本清洗“脏数据”，再到设计 Schema 将语料导入 PostgreSQL。我第一次理解了数据清洗在软件开发中的基础性作用。

2.  **语料库的深度认知**：
    在处理数据的过程中，我深刻理解了 **BNC (British National Corpus)** 与 **MASC (Manually Annotated Sub-Corpus)** 的本质区别——前者严谨、庞大且偏向书面，后者灵活、现代且包含大量口语。这种技术上的处理反过来加深了我对语言学材料的理解。

3.  **开源社区的惊喜**：
    在寻找基础词典数据时，我意外发现了一个宝藏开源项目 **[ECDICT](https://github.com/skywind3000/ECDICT)**。它详尽的数据结构为本项目的基础查询提供了强有力的支持，也让我第一次感受到了开源社区“前人栽树，后人乘凉”的共享精神。

## 🌟 开源愿景 (Open Source Vision)

受限于我的技术背景，目前的版本仍有非常多的局限。我将这个“粗糙”的项目开源，希望对 **NLP (自然语言处理)** 或 **EdTech (教育科技)** 感兴趣的开发者能基于此继续探索，我知道我的项目不足一提，但仍渴望能见到更加优质的产品诞生。

**未来的可能性：**
* **SRS 记忆算法**: 引入间隔重复系统，将“查词”转化为“记忆”。
* **意群网络 (Concept Web)**: 建立用户系统，允许用户构建单词之间的关联网络。
* **浏览器插件化**: 实现网页阅读时的即时 Nuance 分析。

## 🛠️ 技术栈 (Tech Stack)

这是一次非计算机专业学生对全栈开发的尝试：

* **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts
* **Backend**: Python (FastAPI), NLTK (WordNet)
* **Database**: PostgreSQL (JSONB Data Structure)
* **Data Source**: BNC, MASC, ECDICT (Open Source Dictionary)

## 📦 运行指南 (How to Run)

### 1. 环境准备
* PostgreSQL
* Python 3.9+
* Node.js 18+

### 2. 启动后端
```bash
cd NuanceDataEngine
pip install fastapi uvicorn psycopg2 nltk
python server.py

### 2. 启动前端
```bash
cd nuance-web
npm install
npm run dev

***访问地址：http://localhost:3000即可使用

## 💌 致谢与感悟 (Epilogue)

感谢这个技术变革的时代，让像我这样的普通学生也能触碰到创造的门槛。

在项目开发的尾声，当 Gemini 给我那句暖心的鼓励时，我仿佛被带回了刚踏入这个领域的那一瞬间——那种对未知的恐惧，混合着对知识最纯粹的渴求与向往。

即使前路依然困难，但我们已经出发。

---

Created with ❤️ by **A Passionate Learner & Gemini**  
**2026**