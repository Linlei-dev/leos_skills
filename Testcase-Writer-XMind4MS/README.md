# Testcase-Writer-XMind4MS WorkBuddy 技能包 (v2.0)

这是一个 WorkBuddy 技能包。它能够将用户用自然语言或图片等描述的功能需求，自动转换为**严格符合规范、可直接导入 XMind 生成思维导图**的测试用例 Markdown 文档，并**在本地生成可直接导入 MeterSphere 平台的 `.xmind` 文件**。

## 📦 技能包内容
```
Testcase-Writer-XMind4MS/
├── SKILL.md          # 技能主配置文件 (WorkBuddy 读取)
├── FORMAT_SPEC.md    # 核心格式规范 (AI 生成时必须遵守)
├── scripts/          # 本地文件生成脚本目录
│   └── md_to_xmind4ms.py  # Markdown 转 XMind 核心脚本
└── README.md         # 本说明文件
```

## 🎯 核心功能
1.  **智能分析**：用户在 WorkBuddy 中通过触发词 `/生成测试用例` 输入需求，技能调用平台 AI 进行分析。
2.  **规范生成**：AI 严格按照 `FORMAT_SPEC.md` 中的规则，生成结构化的测试用例 Markdown 文档。
3.  **文件生成**：调用 `scripts/md_to_xmind4ms.py` 脚本，将 Markdown 文档转换为标准的 `.xmind` 文件，**保存在 WorkBuddy 调用时传入的本地输出路径**。生成的 XMind 默认使用右向逻辑图，根节点来自 Markdown 第一行的 `# 系统或功能名称测试用例`。
4.  **结果返回**：技能在聊天中返回操作结果，并告知生成文件的**本地绝对路径**。

## 🚀 快速开始 (部署与使用)

### 步骤 1：获取技能
通过 Git 克隆技能仓库：
```bash
git clone https://github.com/Linlei-dev/leos_skills.git
```
技能位于 `leos_skills/Testcase-Writer-XMind4MS/` 目录下。

### 步骤 2：在 WorkBuddy 中加载
1. 进入 WorkBuddy 的"技能管理"页面。
2. 选择"从本地文件夹导入"，指向 `Testcase-Writer-XMind4MS/` 目录。
3. 确认技能加载成功。

### 步骤 3：在 WorkBuddy 中使用
1. 在聊天窗口中使用技能名 `Testcase-Writer-XMind4MS` 或触发词 `/生成测试用例`。
2. 提供需求描述（文字或附加图片），例如：
    > 请为"电商系统的购物车模块"设计测试用例，需要覆盖添加商品、修改数量、删除商品、结算流程，以及库存不足的异常场景。
3. 等待 AI 生成 Markdown 测试用例，并自动调用脚本转换为 XMind 文件。
4. 处理完成后，你将收到类似回复：
    > ✅ 测试用例生成成功！<br>
    > - **XMind 文件路径**：`./output/TC_电商系统_20240520_143022.xmind`

### 步骤 4：获取生成的文件
生成的 `.xmind` 文件默认保存在当前工作目录的 `output/` 子目录下，可直接通过文件浏览器访问。

## ⚙️ 文件与配置详解

### 1. `FORMAT_SPEC.md`
- **定位**：技能的"宪法"。定义了 AI 生成 Markdown 时必须遵循的**所有格式、字段和层级规则**。
- **作用**：确保生成的每一个用例都包含 `文档标题`、`模块路径`、`子模块名称`、`case`、`标签`、`步骤描述`、`预期结果`、`用例等级` 等核心字段，且顺序、缩进、标点完全一致。`# 文档标题` 会作为 XMind 根节点；`## 一级模块-二级模块` 标题下必须直接输出 `- 子模块名称`，禁止重复输出同名模块路径，这是避免 XMind 第二/三层级重复的关键规则。

### 2. `SKILL.md`
- **定位**：技能的"总控开关"和"使用说明书"（给 WorkBuddy 平台和 AI 使用）。
- **包含**：
    - **YAML 头部**：定义了技能名称、触发词、temperature、max_tokens 等参数。
    - **Prompt 正文**：以严格的指令告诉 AI 如何扮演角色、如何工作、必须遵守哪些规范。

### 3. `scripts/md_to_xmind4ms.py`
- **定位**：技能的"后端执行引擎"。
- **作用**：AI 生成 Markdown 后主动调用此脚本，负责：
    1. 解析 Markdown 的结构。
    2. 按照 XMind 的文件格式规范，构建 XML 内容。
    3. 将 XML 及其他必要文件打包成一个 `.xmind` 压缩包。
    4. 将此文件保存到本地输出目录。
- **输出目录**：脚本根据命令行传入的 `<output.xmind>` 路径保存文件；如果目标目录不存在，会自动创建。
- **默认布局**：根主题固定为右向逻辑图，case 下的详情字段默认折叠。

## 🔧 高级配置
- **修改输出目录**：调用 `scripts/md_to_xmind4ms.py <input.md> <output.xmind> [title]` 时传入目标输出路径；脚本会自动创建输出目录。
- **调整生成风格**：在 `SKILL.md` 的 YAML 头部微调 `temperature` (控制随机性) 和 `max_tokens` (控制输出长度)。
- **版本管理**：技能源码托管在 `github.com/Linlei-dev/leos_skills.git`，可通过 Git 进行版本控制和协作更新。

## ❓ 常见问题

**Q1: 生成的 `.xmind` 文件用 XMind 打开后结构乱了吗？**
A1: 请确保 AI 生成的 Markdown 完全符合 `FORMAT_SPEC.md`。最常见的结构错误是**缩进不正确**或**字段缺失/顺序错误**。请用纯文本编辑器检查生成的 `.md` 文件。

**Q2: 技能加载失败或执行报错？**
A2: 请检查：
   1. 技能目录下是否有 `SKILL.md` 文件。
   2. `SKILL.md` 的 YAML 头部格式是否正确。
   3. Python 环境是否可用（脚本需要 Python 3 运行）。

**Q3: 能否生成其他格式（如 Excel、Word）？**
A3: 本技能核心是生成 XMind 兼容的 Markdown。您可以通过修改 `scripts/md_to_xmind4ms.py` 脚本中的解析与打包逻辑，将其替换为生成其他格式的逻辑。

**Q4: AI 生成的用例质量不高怎么办？**
A4: 提供更清晰、更详细的需求描述。您可以在需求中指定模块结构划分，或明确要求包含**正常场景、异常场景、边界场景**的用例。也可以通过更新 `FORMAT_SPEC.md` 和 `SKILL.md` 中的规则来约束 AI 的生成行为。

## 📄 开源与许可
本技能包旨在提供一种自动化测试用例设计的思路。您可以自由地修改、分发并将其用于您的内部项目中。

---
*祝您使用愉快！如果您有改进建议或遇到问题，欢迎反馈。*
