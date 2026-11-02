"""Small, explicitly synthetic VLSI course for trying the workspace offline."""
from copy import deepcopy
from html import escape


DEMO_BUNDLE = {
    "course": {"id": "demo-vlsi", "title": "VLSI 物理设计 · 示例课程", "teacher": "示例内容", "term": "功能演示"},
    "lecture": {"id": "demo-partitioning", "course_id": "demo-vlsi", "title": "从连接到划分：理解 Partitioning",
                "date": "示例课堂", "duration": 1650, "is_demo": True,
                "summary": "这是一份离线功能示例。课程用图模型描述单元与连接，解释 cutsize、面积平衡与初始二划分，再介绍 KL 交换与 FM 单点移动的区别。所有讲稿与知识点均为演示编写，不能作为实际课堂记录。"},
    "slides": [
        {"id": "graph", "title": "用图描述电路", "start": 0, "end": 250, "image_url": "/demo-slides/1.svg",
         "ocr": "Partitioning for VLSI\n用图描述电路\n节点 V = 单元 cells；边 E = 连接 connections\n节点权重表示面积，边权重表示连接代价。\n真实网表的一条 net 可以连接多个单元；简单图是教学近似，超图能保留多端连接。",
         "knowledge": [{"title": "从网表到图", "detail": "把单元抽象为节点、连接抽象为边。简单图便于理解，但多端 net 往往更适合用超图表达。"},
                       {"title": "权重的含义", "detail": "节点权重与边权重承担不同角色：前者可表示面积，后者可表示连接代价。"}]},
        {"id": "cutsize", "title": "Cutsize：跨分区的连接代价", "start": 250, "end": 530, "image_url": "/demo-slides/2.svg",
         "ocr": "Cutsize\nV = A ∪ B，A ∩ B = ∅\ncut(A,B) = Σ w(u,v)，其中 u∈A、v∈B\n只统计端点跨越分区的边，分区内部的边不计入 cutsize。\n本例中跨区边权为 2、3，cutsize = 5。",
         "knowledge": [{"title": "加权 cutsize", "detail": "对跨分区边的权重求和；只有所有边权均为 1 时，cutsize 才等于跨区边数。"},
                       {"title": "内部连接不计入", "detail": "同一分区内的连接保留在内部，不能把图中的全部边权都加到 cutsize 中。"}]},
        {"id": "balance", "title": "平衡的是面积，不只是数量", "start": 530, "end": 820, "image_url": "/demo-slides/3.svg",
         "ocr": "Balance\nS_A = Σ area(v)，v∈A；S_B = Σ area(v)，v∈B\nNormalized imbalance = |S_A - S_B| / (S_A + S_B)\n本例 S_A=12、S_B=8，不平衡度为 4/20 = 0.20。\n选择划分时需要同时考虑 cutsize 和平衡约束。",
         "knowledge": [{"title": "面积平衡", "detail": "节点数相同不保证面积相同。存在节点权重时，应根据面积总和评估约束。"},
                       {"title": "归一化不平衡度", "detail": "本示例采用 |S_A−S_B|/(S_A+S_B)，12 与 8 对应 0.20。不同工具可能采用不同定义，应核对公式。"}]},
        {"id": "initial", "title": "初始二划分：先得到可行解", "start": 820, "end": 1080, "image_url": "/demo-slides/4.svg",
         "ocr": "Initial Bipartition\nRandom：随机分配，再检查面积约束\nGreedy / region growing：依据连接关系逐步扩展\n初始解影响后续局部改进的轨迹。\n比较策略时：固定输入、约束、随机种子，重复实验。",
         "knowledge": [{"title": "可行性先于比较", "detail": "评价 cutsize 前应先确认分区满足非空、完整分配和面积约束。"},
                       {"title": "可复现实验", "detail": "固定图、平衡约束和随机种子，多次比较结果，避免只依据一次随机运行下结论。"}]},
        {"id": "kl-fm", "title": "KL 与 FM：两种局部改进", "start": 1080, "end": 1400, "image_url": "/demo-slides/5.svg",
         "ocr": "Local Refinement\nKernighan–Lin (KL)：成对交换分区中的节点\nFiduccia–Mattheyses (FM)：基于 gain 选择单节点移动\n每一步移动都需要考虑约束。\n一轮探索后保留累计收益最好的可行前缀，收益不能只看某一步。",
         "knowledge": [{"title": "交换与移动", "detail": "经典 KL 以节点对交换为基本操作，FM 以单节点移动为基本操作；具体实现还需考虑面积等约束。"},
                       {"title": "累计收益", "detail": "局部改进的一轮探索可以包含临时不改善的操作，通常根据累计收益选择保留的前缀。"}]},
        {"id": "recap", "title": "把方法放回同一个评价框架", "start": 1400, "end": 1650, "image_url": "/demo-slides/6.svg",
         "ocr": "A reproducible workflow\n建模 → 初始划分 → 局部改进 → 验证\n检查：每个单元仅属于一个分区；满足面积约束；重算 cutsize。\n自测：面积为 12 和 8 时，不平衡度是多少？\n讨论：降低 cutsize 是否一定能得到更好的可行解？",
         "knowledge": [{"title": "四步工作流", "detail": "把建模、初始化、改进与验证分开记录，才能定位结果差异来自哪一步。"},
                       {"title": "约束与目标", "detail": "较低的 cutsize 不能弥补违反面积约束的问题，比较时必须同时报告可行性。"}]},
    ],
    "transcript": [
        {"start": 0, "end": 48, "text": "欢迎使用这份功能演示。下面的讲稿是合成示例，不是真实课堂录音。我们用电路划分来体验 slides、讲稿、知识点和问答之间的关联。"},
        {"start": 48, "end": 130, "text": "先把电路里的单元看成节点，把连接看成边。节点权重可以表示面积，边权重可以表示连接代价。两个权重不是同一件事。"},
        {"start": 130, "end": 250, "text": "真实网表的一个 net 可能连接多个单元。今天用简单图解释基本概念，更精确的多端连接可以用超图表达。选用什么模型，要与目标函数保持一致。"},
        {"start": 250, "end": 360, "text": "现在把节点分成 A 和 B。cutsize 只计算跨区的连接代价。A 内部或者 B 内部的边不计入。假设跨区边权为二和三，那么 cutsize 就是五。"},
        {"start": 360, "end": 450, "text": "注意，加权图中的 cutsize 不是简单数边。只有边权都为一的时候，数跨区边与求权重和才一样。"},
        {"start": 450, "end": 530, "text": "如果把所有节点都放进同一边，跨区代价可能很小，但这种结果往往不满足我们的划分要求。所以目标函数必须与约束一起考虑。"},
        {"start": 530, "end": 640, "text": "平衡通常应根据面积来算，不只是根据节点数。三颗大的单元可能比五颗小单元占用更多面积。请分别求出 A 与 B 的节点面积和。"},
        {"start": 640, "end": 750, "text": "本示例把归一化不平衡度定义为两边面积差的绝对值，除以总面积。如果 A 为十二、B 为八，结果是四除以二十，也就是零点二。"},
        {"start": 750, "end": 820, "text": "工具对 balance ratio 和 imbalance 的定义可能不一样，不能只凭名称比较数值。请在实验报告里写出使用的公式。"},
        {"start": 820, "end": 940, "text": "初始二划分先提供一个起点。随机策略容易实现，贪心或区域增长策略可以利用连接信息。但它们都要检查面积约束，不能只追求内部连接紧密。"},
        {"start": 940, "end": 1080, "text": "比较初始方法时，要使用相同输入和约束。随机算法固定种子并重复运行，报告结果的变化，而不是选择最好的一次当作全部结论。"},
        {"start": 1080, "end": 1200, "text": "经典 KL 的基本动作是从两边各选择一个节点成对交换。FM 则以单个节点移动为基本动作，通过 gain 来组织候选。具体实现需要检查移动是否合法。"},
        {"start": 1200, "end": 1320, "text": "一轮局部改进中，我们可以探索多个操作，再找累计收益最大的可行前缀。不要只看某一步的收益，也不要在没有验证约束的情况下保留操作。"},
        {"start": 1320, "end": 1400, "text": "节点有不同面积时，成对交换也未必保持面积相等。这正好提醒我们，经典算法的简单假设与实际实现的约束需要分开看。"},
        {"start": 1400, "end": 1530, "text": "把整个流程分成建模、初始划分、局部改进和验证四步。验证阶段重新计算 cutsize，检查每个节点是否只在一个分区，以及面积约束是否满足。"},
        {"start": 1530, "end": 1650, "text": "最后用两个问题自测：十二和八对应的不平衡度是多少？如果一个方案的 cutsize 更小，但违反了面积约束，我们能直接说它更好吗？请回到课件和原文找证据。"},
    ],
}


def demo_bundle():
    return deepcopy(DEMO_BUNDLE)


def demo_slide_svg(number):
    """Return an inline vector deck; no binary assets or video downloads."""
    number = int(number)
    if number < 1 or number > len(DEMO_BUNDLE["slides"]):
        raise KeyError("示例幻灯片不存在")
    slide = DEMO_BUNDLE["slides"][number - 1]
    subtitles = [
        "From a netlist to a weighted graph", "Minimize connections across the boundary",
        "COUNT IS NOT AREA", "Start feasible. Refine deliberately.",
        "Exchange pairs. Move one cell.", "Model → Initialize → Refine → Verify",
    ]
    body = []
    if number in (1, 2, 4):
        coords = [(330, 235), (485, 165), (465, 355), (735, 220), (830, 370), (675, 425)]
        edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 5), (3, 4), (4, 5)]
        if number in (2, 4):
            body += ['<rect x="240" y="125" width="330" height="360" rx="22" fill="#e8efff"/>',
                     '<rect x="610" y="125" width="330" height="360" rx="22" fill="#e8f3ee"/>',
                     '<text x="270" y="160" class="small">PARTITION A</text>', '<text x="640" y="160" class="small">PARTITION B</text>']
        for a, b in edges:
            cross = number == 2 and (a, b) in ((1, 3), (2, 5))
            x1, y1 = coords[a]
            x2, y2 = coords[b]
            body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s/>' %
                        (x1, y1, x2, y2, "#c7673a" if cross else "#a3b3bd", 5 if cross else 3,
                         ' stroke-dasharray="10 6"' if cross else ""))
            if cross:
                body.append('<text x="%s" y="%s" class="label" fill="#b25a31">%s</text>' % ((x1+x2)//2, (y1+y2)//2-14, 2 if a == 1 else 3))
        for i, (x, y) in enumerate(coords):
            body += ['<circle cx="%s" cy="%s" r="31" fill="%s"/>' % (x, y, "#3b64b4" if i < 3 else "#467b68"),
                     '<text x="%s" y="%s" text-anchor="middle" fill="white" class="label">%s</text>' % (x, y+8, chr(65+i))]
        if number == 2:
            body.append('<text x="960" y="295" class="big" text-anchor="middle">5</text><text x="960" y="330" class="small" text-anchor="middle">CUTSIZE</text>')
    elif number == 3:
        body += ['<rect x="225" y="190" width="350" height="245" rx="24" fill="#e8efff"/>',
                 '<rect x="625" y="190" width="350" height="245" rx="24" fill="#e8f3ee"/>',
                 '<text x="400" y="280" class="big" text-anchor="middle">12</text>',
                 '<text x="800" y="280" class="big" text-anchor="middle">8</text>',
                 '<text x="400" y="325" class="small" text-anchor="middle">AREA OF A</text>',
                 '<text x="800" y="325" class="small" text-anchor="middle">AREA OF B</text>',
                 '<text x="600" y="500" class="label" text-anchor="middle">|12 − 8| / (12 + 8) = 0.20</text>']
    elif number == 5:
        body += ['<rect x="150" y="170" width="420" height="310" rx="24" fill="#e8efff"/>',
                 '<rect x="625" y="170" width="420" height="310" rx="24" fill="#e8f3ee"/>',
                 '<text x="190" y="235" class="big">KL</text><text x="665" y="235" class="big">FM</text>',
                 '<text x="190" y="287" class="label">成对交换</text><text x="665" y="287" class="label">单节点移动</text>',
                 '<text x="190" y="350" class="small">Pair exchange</text><text x="665" y="350" class="small">Gain-based moves</text>',
                 '<text x="600" y="530" class="small" text-anchor="middle">评估累计收益，始终核对约束</text>']
    else:
        for i, (title, subtitle) in enumerate([("01", "建模"), ("02", "初始划分"), ("03", "局部改进"), ("04", "验证")]):
            x = 120 + i * 270
            body += ['<rect x="%d" y="220" width="235" height="220" rx="24" fill="%s"/>' % (x, "#e8efff" if i % 2 == 0 else "#e8f3ee"),
                     '<text x="%d" y="295" class="big">%s</text>' % (x+30, title),
                     '<text x="%d" y="355" class="label">%s</text>' % (x+30, subtitle)]
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="%s">
<rect width="1200" height="675" fill="#fbfcfe"/>
<style>text{font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;fill:#253951}.small{font-size:19px;fill:#6c7d8e}.label{font-size:25px;font-weight:600}.big{font-size:60px;font-weight:700}</style>
<text x="65" y="60" class="small" letter-spacing="3">CANVAS SYNAPSE · SYNTHETIC DEMO</text>
<text x="65" y="110" font-size="34" font-weight="700">%s</text>
%s
<line x1="65" y1="600" x2="1135" y2="600" stroke="#dce3ec"/>
<text x="65" y="639" class="small">%s</text>
<text x="1135" y="639" class="small" text-anchor="end">%02d / 06 · 示例课件</text>
</svg>''' % (escape(slide["title"]), escape(slide["title"]), "\n".join(body), escape(subtitles[number - 1]), number)
