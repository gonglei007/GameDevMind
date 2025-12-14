#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XMind to Markdown Converter
将 XMind 文件转换为 Markdown 格式
"""

import os
import sys
import zipfile
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def extract_xmind_content(xmind_file):
    """从 XMind 文件中提取内容"""
    try:
        # XMind 文件实际上是一个 ZIP 文件
        with zipfile.ZipFile(xmind_file, 'r') as zip_ref:
            # 读取 content.xml
            if 'content.xml' in zip_ref.namelist():
                content = zip_ref.read('content.xml')
                return content.decode('utf-8')
            else:
                # 尝试读取 xmind 格式的内容
                for name in zip_ref.namelist():
                    if name.endswith('.xml') and 'content' in name.lower():
                        content = zip_ref.read(name)
                        return content.decode('utf-8')
    except Exception as e:
        print(f"Error reading XMind file: {e}", file=sys.stderr)
        return None


def parse_xmind_xml(xml_content):
    """解析 XMind XML 内容并转换为 Markdown"""
    try:
        root = ET.fromstring(xml_content)
        
        # 查找主题节点
        topics = root.findall('.//{http://www.xmind.org/xmind/core/v1}topic')
        
        if not topics:
            # 尝试不同的命名空间
            topics = root.findall('.//topic')
        
        if not topics:
            return "# XMind Content\n\n无法解析 XMind 文件内容。\n"
        
        # 获取根主题
        root_topic = topics[0]
        markdown = []
        
        def process_topic(topic, level=1):
            """递归处理主题节点"""
            title_elem = topic.find('.//{http://www.xmind.org/xmind/core/v1}title')
            if title_elem is None:
                title_elem = topic.find('title')
            
            if title_elem is not None and title_elem.text:
                title = title_elem.text.strip()
                if title:
                    # 根据层级添加 Markdown 标题
                    markdown.append(f"{'#' * level} {title}\n")
            
            # 处理子主题
            children = topic.findall('.//{http://www.xmind.org/xmind/core/v1}children')
            if not children:
                children = topic.findall('children')
            
            for child in children:
                topics_elem = child.find('.//{http://www.xmind.org/xmind/core/v1}topics')
                if topics_elem is None:
                    topics_elem = child.find('topics')
                
                if topics_elem is not None:
                    child_topics = topics_elem.findall('.//{http://www.xmind.org/xmind/core/v1}topic')
                    if not child_topics:
                        child_topics = topics_elem.findall('topic')
                    
                    for child_topic in child_topics:
                        process_topic(child_topic, level + 1)
        
        process_topic(root_topic)
        
        return '\n'.join(markdown) if markdown else "# XMind Content\n\n内容为空。\n"
    
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        # 尝试使用 xmindparser 库（如果可用）
        try:
            import xmindparser
            workbook = xmindparser.xmind_to_dict(xml_content)
            return convert_dict_to_markdown(workbook)
        except ImportError:
            return f"# XMind Content\n\n解析错误: {e}\n\n提示: 可以尝试安装 xmindparser 库: pip install xmindparser\n"
        except Exception as e2:
            return f"# XMind Content\n\n解析错误: {e2}\n"


def convert_dict_to_markdown(workbook, level=1):
    """将 xmindparser 解析的字典转换为 Markdown"""
    markdown = []
    
    if isinstance(workbook, dict):
        for sheet in workbook.get('sheets', []):
            root_topic = sheet.get('topic', {})
            markdown.append(process_topic_dict(root_topic, level))
    elif isinstance(workbook, list):
        for item in workbook:
            markdown.append(process_topic_dict(item, level))
    
    return '\n'.join(markdown) if markdown else "# XMind Content\n\n内容为空。\n"


def process_topic_dict(topic, level=1):
    """递归处理主题字典"""
    if not isinstance(topic, dict):
        return ""
    
    markdown = []
    title = topic.get('title', '').strip()
    
    if title:
        markdown.append(f"{'#' * level} {title}\n")
    
    # 处理备注
    notes = topic.get('note', '')
    if notes:
        markdown.append(f"\n{notes}\n")
    
    # 处理子主题
    children = topic.get('topics', [])
    for child in children:
        markdown.append(process_topic_dict(child, level + 1))
    
    return '\n'.join(markdown)


def xmind_to_markdown(xmind_file, output_file=None):
    """将 XMind 文件转换为 Markdown"""
    if not os.path.exists(xmind_file):
        print(f"Error: XMind file not found: {xmind_file}", file=sys.stderr)
        return False
    
    # 提取内容
    xml_content = extract_xmind_content(xmind_file)
    if xml_content is None:
        print(f"Error: Failed to extract content from {xmind_file}", file=sys.stderr)
        return False
    
    # 尝试使用 xmindparser 库（如果可用）
    try:
        import xmindparser
        workbook = xmindparser.xmind_to_dict(xmind_file)
        markdown_content = convert_dict_to_markdown(workbook)
    except ImportError:
        # 如果没有安装 xmindparser，使用 XML 解析
        markdown_content = parse_xmind_xml(xml_content)
    except Exception as e:
        print(f"Warning: xmindparser failed, using XML parser: {e}", file=sys.stderr)
        markdown_content = parse_xmind_xml(xml_content)
    
    # 确定输出文件路径
    if output_file is None:
        output_file = os.path.splitext(xmind_file)[0] + '.md'
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 写入 Markdown 文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Successfully converted: {xmind_file} -> {output_file}")
        return True
    except Exception as e:
        print(f"Error writing Markdown file: {e}", file=sys.stderr)
        return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python xmind2md.py <xmind_file> [output_file]")
        print("   or: python xmind2md.py <xmind_file>")
        sys.exit(1)
    
    xmind_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = xmind_to_markdown(xmind_file, output_file)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

