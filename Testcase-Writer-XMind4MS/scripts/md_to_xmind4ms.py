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
import uuid
import tempfile
from datetime import datetime
from pathlib import Path

def parse_markdown_to_tree(md_content):
    """
    严格按层级解析Markdown：
    # 一级标题 -> 根节点
    ## 二级标题 -> 二级节点（独立模块）
    - 列表项 -> 三级及以下节点（根据缩进）
    """
    lines = md_content.split('\n')
    root = None
    stack = []  # 用于维护当前路径的栈
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        
        # 1. 处理一级标题 (# 开头)
        if line.startswith('# '):
            level = 1
            text = line.lstrip('#').strip()
            
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

def create_xmind_topic(node, topic_id="root"):
    """创建XMind主题节点"""
    topic = {
        "id": topic_id,
        "title": node['text'],
        "children": {
            "attached": []
        }
    }
    
    # 递归创建子主题
    for idx, child in enumerate(node['children']):
        child_id = f"{topic_id}_{idx}"
        child_topic = create_xmind_topic(child, child_id)
        topic['children']['attached'].append(child_topic)
    
    # 如果没有子节点，移除children字段（避免空结构）
    if not topic['children']['attached']:
        del topic['children']
    
    return topic

def create_xmind_content(tree, title="测试用例"):
    """创建XMind content.json内容"""
    content = [{
        "id": "sheet_1",
        "title": title,
        "rootTopic": create_xmind_topic(tree, "root")
    }]
    return content

def create_manifest():
    """创建manifest.json"""
    return {
        "file-entries": {
            "content.json": {},
            "metadata.json": {}
        }
    }

def create_metadata():
    """创建metadata.json"""
    return {
        "creator": {
            "name": "TestCase Converter",
            "version": "1.0"
        },
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modified": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def convert_md_to_xmind(md_file_path, xmind_file_path, title="测试用例"):
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
    
    # 创建临时目录
    temp_dir = "/tmp/xmind_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
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
    
    # 清理临时文件
    import shutil
    shutil.rmtree(temp_dir)
    
    print("✅ 转换完成！")
    print(f"   XMind文件已保存到: {xmind_file_path}")
    
    # 统计信息
    total_nodes = count_nodes(tree)
    print(f"   总节点数: {total_nodes}")
    
    return xmind_file_path

def count_nodes(node):
    """统计节点总数"""
    count = 1
    for child in node['children']:
        count += count_nodes(child)
    return count

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python md_to_xmind_final.py <input.md> <output.xmind> [title]")
        sys.exit(1)
    
    md_file = sys.argv[1]
    xmind_file = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "测试用例"
    
    convert_md_to_xmind(md_file, xmind_file, title)