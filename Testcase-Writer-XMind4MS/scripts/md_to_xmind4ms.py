#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将Markdown测试用例转换为可直接导入metersphere平台的XMind文件
"""

import json
import zipfile
import os
import re
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DETAIL_FIELD_PREFIXES = (
    "标签:",
    "前置条件:",
    "步骤描述:",
    "步骤:",
    "预期结果:",
    "用例等级:",
)


def normalize_root_title(text: str) -> str:
    """将根节点标题统一为“系统/功能名称测试用例”。"""
    title = text.strip()
    if not title:
        return "测试用例思维导图"
    if title.endswith("测试用例"):
        return title
    return f"{title}测试用例"


def infer_root_title_from_module(module_path: str) -> str:
    """从模块路径兜底推断根节点标题，如“系统管理-操作手册管理-模块分类管理” -> “操作手册管理测试用例”。"""
    parts = [part.strip() for part in re.split(r"[-－—/]", module_path) if part.strip()]
    if len(parts) >= 2:
        return normalize_root_title(parts[1])
    if parts:
        return normalize_root_title(parts[0])
    return "测试用例思维导图"


def is_case_topic(text: str) -> bool:
    return text.strip().lower().startswith("case:")


def is_detail_field_topic(text: str) -> bool:
    clean_text = text.strip()
    return any(clean_text.startswith(prefix) for prefix in DETAIL_FIELD_PREFIXES)


def parse_markdown_to_tree(md_content: str) -> Dict[str, Any]:
    """
    严格按层级解析Markdown：
    # 一级标题 -> 根节点
    ## 二级标题 -> 二级节点（独立模块）
    - 列表项 -> 三级及以下节点（根据缩进）
    """
    lines = md_content.replace('\ufeff', '').split('\n')
    root = None
    stack = []  # 用于维护当前路径的栈
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        
        # 1. 处理一级标题 (# 开头)
        if line.startswith('# '):
            level = 1
            text = normalize_root_title(line.lstrip('#').strip())
            
            node = {'level': level, 'text': text, 'children': []}
            
            if root is None:
                root = node
                stack = [root]
            else:
                # 找到父节点（一级标题的父节点是根）
                while len(stack) > 0 and stack[-1]['level'] >= level:
                    stack.pop()
                if stack:
                    stack[-1]['children'].append(node)
                stack.append(node)
        
        # 2. 处理二级标题 (## 开头) —— 关键修复！
        elif line.startswith('## '):
            level = 2
            text = line.lstrip('#').strip()

            if root is None:
                root = {'level': 1, 'text': infer_root_title_from_module(text), 'children': []}
                stack = [root]
            
            node = {'level': level, 'text': text, 'children': []}
            
            # 二级标题的父节点是一级标题
            while len(stack) > 0 and stack[-1]['level'] >= level:
                stack.pop()
            if stack:
                stack[-1]['children'].append(node)
            stack.append(node)
        
        # 3. 处理列表项 (- 开头) —— 根据缩进判断层级
        elif line.strip().startswith('-'):
            # 计算缩进空格数（每2个空格为一级）
            indent = len(line) - len(line.lstrip())
            text = line.strip().lstrip('-').strip()
            
            # 移除checkbox标记
            text = re.sub(r'^\[ \] ', '☐ ', text)
            text = re.sub(r'^\[x\] ', '☑ ', text)
            
            # 移除粗体标记
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            
            if text:
                # 列表层级：从3级开始（因为1级是#，2级是##）
                list_level = 3 + (indent // 2)

                # 兼容旧版规范：如果##标题下紧跟同名一级列表项，则跳过，避免XMind第二/三层重复。
                if (
                    list_level == 3
                    and stack
                    and stack[-1]['level'] == 2
                    and stack[-1]['text'] == text
                ):
                    continue
                
                node = {'level': list_level, 'text': text, 'children': []}
                
                # 找到父节点（根据层级回退栈）
                while len(stack) > 0 and stack[-1]['level'] >= list_level:
                    stack.pop()
                if stack:
                    stack[-1]['children'].append(node)
                stack.append(node)
    
    # 如果没有找到任何标题，创建默认根节点
    if root is None:
        root = {'level': 1, 'text': '测试用例思维导图', 'children': []}
    
    return root


def validate_markdown(md_content: str) -> Tuple[bool, List[str]]:
    """校验 Markdown 格式是否符合规范，返回 (是否通过, 错误列表)"""
    errors: List[str] = []
    lines = md_content.replace('\ufeff', '').split('\n')
    
    # 检查1: 第一行必须是一级标题
    first_line = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break
    if not first_line.startswith('# '):
        errors.append("文档首行必须是一级标题 `# <系统名称>测试用例`")
    
    # 检查2: 每个 ## 下面必须有内容
    in_section = False
    section_has_content = False
    section_name = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## '):
            if in_section and not section_has_content:
                errors.append(f"模块 `{section_name}` 下没有测试用例内容")
            in_section = True
            section_has_content = False
            section_name = stripped[3:].strip()
        elif in_section and stripped.startswith('-') and ('case:' in stripped or stripped.lstrip('-').strip()):
            section_has_content = True
    
    if in_section and not section_has_content:
        errors.append(f"模块 `{section_name}` 下没有测试用例内容")
    
    # 检查3: case 条目必须有所有必填字段
    case_lines = [l for l in lines if l.strip().startswith('- case:')]
    if not case_lines:
        errors.append("文档中未找到任何 `case:` 条目，请检查格式")
    
    return len(errors) == 0, errors


def create_xmind_topic(node: Dict[str, Any], topic_id: str = "root", depth: int = 1) -> Dict[str, Any]:
    """创建XMind主题节点"""
    topic = {
        "id": topic_id,
        "title": node['text'],
        "children": {
            "attached": []
        }
    }

    if depth == 1:
        topic["structureClass"] = "org.xmind.ui.logic.right"

    if is_case_topic(node['text']) and node['children']:
        topic["folded"] = True

    if is_detail_field_topic(node['text']) and node['children']:
        topic["folded"] = True
    
    # 递归创建子主题
    for idx, child in enumerate(node['children']):
        child_id = f"{topic_id}_{idx}"
        child_topic = create_xmind_topic(child, child_id, depth + 1)
        topic['children']['attached'].append(child_topic)
    
    # 如果没有子节点，移除children字段（避免空结构）
    if not topic['children']['attached']:
        del topic['children']
    
    return topic

def create_xmind_content(tree: Dict[str, Any], title: str = "测试用例") -> List[Dict[str, Any]]:
    """创建XMind content.json内容"""
    content = [{
        "id": "sheet_1",
        "title": title,
        "rootTopic": create_xmind_topic(tree, "root")
    }]
    return content

def create_manifest() -> Dict[str, Any]:
    """创建manifest.json"""
    return {
        "file-entries": {
            "content.json": {},
            "metadata.json": {}
        }
    }

def create_metadata() -> Dict[str, Any]:
    """创建metadata.json"""
    return {
        "creator": {
            "name": "TestCase Converter",
            "version": "1.0"
        },
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def convert_md_to_xmind(md_file_path: str, xmind_file_path: str, title: str = "测试用例") -> str:
    """将Markdown文件转换为XMind文件"""
    print(f"正在读取Markdown文件: {md_file_path}")
    
    # 读取Markdown文件
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    print("正在解析Markdown内容...")
    # 解析Markdown为树形结构
    tree = parse_markdown_to_tree(md_content)
    
    print("正在创建XMind文档...")
    # 创建XMind内容
    content = create_xmind_content(tree, title)
    manifest = create_manifest()
    metadata = create_metadata()
    
    output_dir = os.path.dirname(os.path.abspath(xmind_file_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="xmind_temp_") as temp_dir:
        # 保存JSON文件到临时目录
        with open(os.path.join(temp_dir, "manifest.json"), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        with open(os.path.join(temp_dir, "content.json"), 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

        with open(os.path.join(temp_dir, "metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 创建XMind文件（ZIP格式）
        print(f"正在保存XMind文件: {xmind_file_path}")
        with zipfile.ZipFile(xmind_file_path, 'w', zipfile.ZIP_DEFLATED) as xmind_zip:
            xmind_zip.write(os.path.join(temp_dir, "manifest.json"), "manifest.json")
            xmind_zip.write(os.path.join(temp_dir, "content.json"), "content.json")
            xmind_zip.write(os.path.join(temp_dir, "metadata.json"), "metadata.json")

    print("转换完成！")
    print(f"   XMind文件已保存到: {xmind_file_path}")
    
    # 统计信息
    total_nodes = count_nodes(tree)
    print(f"   总节点数: {total_nodes}")
    
    return xmind_file_path

def count_nodes(node: Dict[str, Any]) -> int:
    """统计节点总数"""
    count = 1
    for child in node.get('children', []):
        count += count_nodes(child)
    return count

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  转换模式: python md_to_xmind4ms.py <input.md> <output.xmind> [title]")
        print("  校验模式: python md_to_xmind4ms.py --validate <input.md>")
        sys.exit(1)
    
    # 校验模式
    if sys.argv[1] == '--validate':
        if len(sys.argv) < 3:
            print("错误: 校验模式需要指定输入文件")
            print("用法: python md_to_xmind4ms.py --validate <input.md>")
            sys.exit(1)
        md_file = sys.argv[2]
        if not os.path.exists(md_file):
            print(f"错误: 文件不存在 - {md_file}")
            sys.exit(1)
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        passed, errors = validate_markdown(content)
        if passed:
            print(f"校验通过: {md_file}")
        else:
            print(f"校验失败: {md_file}")
            for err in errors:
                print(f"  - {err}")
        sys.exit(0 if passed else 1)
    
    # 转换模式
    if len(sys.argv) < 3:
        print("错误: 参数不足")
        print("用法: python md_to_xmind4ms.py <input.md> <output.xmind> [title]")
        sys.exit(1)
    
    md_file = sys.argv[1]
    xmind_file = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "测试用例"
    
    if not os.path.exists(md_file):
        print(f"错误: 输入文件不存在 - {md_file}")
        sys.exit(1)
    
    convert_md_to_xmind(md_file, xmind_file, title)
