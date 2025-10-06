#!/usr/bin/env python3
"""
USX File Splitter

This script converts a single USX file into smaller USX files based on a TOC structure.
It reads the TOC YAML file to understand the chapter and chunk organization,
then splits the content accordingly.
"""

import os
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path
import re


class USXSplitter:
    def __init__(self, usx_file_path, toc_file_path, output_dir):
        self.usx_file_path = usx_file_path
        self.toc_file_path = toc_file_path
        self.output_dir = Path(output_dir)
        self.toc_data = None
        self.usx_content = None
        
    def load_toc(self):
        """Load and parse the TOC YAML file."""
        with open(self.toc_file_path, 'r', encoding='utf-8') as f:
            self.toc_data = yaml.safe_load(f)
        print(f"Loaded TOC with {len(self.toc_data)} chapters")
        
    def load_usx(self):
        """Load and parse the USX XML file."""
        tree = ET.parse(self.usx_file_path)
        self.usx_content = tree.getroot()
        print(f"Loaded USX file: {self.usx_content.tag}")
        
    def extract_chapter_content(self, chapter_num):
        """Extract all content for a specific chapter."""
        chapter_content = []
        in_target_chapter = False
        found_start = False
        
        for element in self.usx_content:
            if element.tag == 'chapter':
                if element.get('number') == str(chapter_num) and element.get('eid') is None:
                    # This is the start of our target chapter
                    in_target_chapter = True
                    found_start = True
                    chapter_content.append(element)
                elif element.get('number') != str(chapter_num) and in_target_chapter:
                    # We've moved to a different chapter, stop collecting
                    break
                elif element.get('eid') is not None and in_target_chapter:
                    # This is the end of our target chapter
                    chapter_content.append(element)
                    break
            elif in_target_chapter:
                # We're inside the target chapter, collect this element
                chapter_content.append(element)
        
        if not found_start:
            print(f"Warning: Chapter {chapter_num} start marker not found")
                
        return chapter_content
    
    def extract_verses_for_chunk(self, chapter_content, start_verse, end_verse=None):
        """Extract verses for a specific chunk within a chapter."""
        if end_verse is None:
            end_verse = start_verse
            
        chunk_content = []
        
        for element in chapter_content:
            if element.tag == 'para':
                # Check if this paragraph contains verses in our range
                verses_in_para = self.extract_verses_from_para(element, start_verse, end_verse)
                if verses_in_para:
                    chunk_content.append(verses_in_para)
            elif element.tag == 'chapter' and element.get('eid') is None:
                # Chapter start marker - include in all chunks
                chunk_content.append(element)
                
        return chunk_content
    
    def extract_verses_from_para(self, para_element, start_verse, end_verse):
        """Extract verses from a paragraph element that fall within the specified range."""
        # Check if this paragraph contains any verses in our range
        has_verses_in_range = False
        for child in para_element:
            if child.tag == 'verse':
                verse_num = int(child.get('number', 0))
                if start_verse <= verse_num <= end_verse:
                    has_verses_in_range = True
                    break
                    
        if not has_verses_in_range:
            return None
            
        # Create a copy of the paragraph
        para_copy = ET.Element(para_element.tag, para_element.attrib)
        
        # Process all text and elements within the paragraph
        current_text = ""
        for child in para_element:
            if child.tag == 'verse':
                verse_num = int(child.get('number', 0))
                if start_verse <= verse_num <= end_verse:
                    # This verse is in our range, include it
                    para_copy.append(child)
                    # Add any text that follows this verse
                    if child.tail:
                        current_text += child.tail
            else:
                # Other elements (like notes) - include if they're within our verse range
                para_copy.append(child)
                if child.tail:
                    current_text += child.tail
                    
        # Add any remaining text
        if para_element.text:
            current_text = para_element.text + current_text
            
        if current_text.strip():
            para_copy.text = current_text
            
        # Only return the paragraph if it has content
        if len(para_copy) > 0 or (para_copy.text and para_copy.text.strip()):
            return para_copy
        return None
    
    def create_chunk_file(self, chapter_num, chunk_num, content, is_title=False):
        """Create a USX file for a specific chunk."""
        # Create chapter directory
        chapter_dir = self.output_dir / f"{chapter_num:02d}"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if is_title:
            filename = "title.usx"
        else:
            filename = f"{chunk_num:02d}.usx"
            
        file_path = chapter_dir / filename
        
        # Create the USX document
        usx_root = ET.Element('usx', version='3.0')
        
        # Add book information for non-title chunks
        if not is_title:
            book_info = ET.SubElement(usx_root, 'book', code='REV', style='id')
            book_info.text = '- Biblica® Open Vietnamese Contemporary Bible 2015 (Biblica® Thiên Ban Kinh Thánh Hiện Đại)'
        
        # Add the content (including chapter markers if present)
        for element in content:
            if element is not None:
                usx_root.append(element)
        
        # Add chapter end marker for non-title chunks if not already present
        if not is_title:
            has_chapter_end = any(elem.tag == 'chapter' and elem.get('eid') for elem in content)
            if not has_chapter_end:
                chapter_end = ET.SubElement(usx_root, 'chapter', eid=f'REV {chapter_num}')
        
        # Write the file
        tree = ET.ElementTree(usx_root)
        self._indent_xml(usx_root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
        print(f"Created: {file_path}")
        
    def process_chapter(self, chapter_info):
        """Process a single chapter according to the TOC structure."""
        chapter_num = chapter_info['chapter']
        chunks = chapter_info['chunks']
        
        print(f"Processing chapter {chapter_num} with {len(chunks)} chunks")
        
        # Extract all content for this chapter
        chapter_content = self.extract_chapter_content(chapter_num)
        
        if not chapter_content:
            print(f"Warning: No content found for chapter {chapter_num}")
            return
            
        # Process each chunk
        for i, chunk in enumerate(chunks):
            if chunk == 'title':
                # Create title file
                title_content = self.extract_title_content(chapter_content)
                self.create_chunk_file(int(chapter_num), 0, title_content, is_title=True)
            else:
                # Create regular chunk file
                chunk_num = int(chunk)
                chunk_content = self.extract_verses_for_chunk(chapter_content, chunk_num)
                self.create_chunk_file(int(chapter_num), chunk_num, chunk_content)
    
    def extract_title_content(self, chapter_content):
        """Extract title content for a chapter."""
        title_content = []
        
        for element in chapter_content:
            if element.tag == 'para' and element.get('style') in ['s1', 's2', 's3', 'mt1', 'mt2', 'mt3']:
                title_content.append(element)
            elif element.tag == 'chapter' and element.get('eid') is None:
                # Include chapter marker in title
                title_content.append(element)
                
        return title_content
    
    def _indent_xml(self, elem, level=0):
        """Add indentation to XML elements for better readability."""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for child in elem:
                self._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def run(self):
        """Main execution method."""
        print("Starting USX splitting process...")
        
        # Load data
        self.load_toc()
        self.load_usx()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each chapter
        for chapter_info in self.toc_data:
            if chapter_info['chapter'] == 'front':
                # Handle front matter
                self.process_front_matter(chapter_info)
            else:
                # Handle regular chapters
                self.process_chapter(chapter_info)
        
        print("USX splitting completed!")
    
    def process_front_matter(self, front_info):
        """Process front matter (title page, etc.)."""
        print("Processing front matter...")
        
        # Create front directory
        front_dir = self.output_dir / "front"
        front_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract front matter content
        front_content = []
        for element in self.usx_content:
            if element.tag in ['book', 'para'] and element.get('style') in ['h', 'toc1', 'toc2', 'toc3', 'mt1', 'mt2', 'mt3']:
                front_content.append(element)
            elif element.tag == 'chapter':
                # Stop at first chapter
                break
                
        # Create title file
        if front_content:
            usx_root = ET.Element('usx', version='3.0')
            for element in front_content:
                usx_root.append(element)
            
            tree = ET.ElementTree(usx_root)
            self._indent_xml(usx_root)
            tree.write(front_dir / "title.usx", encoding='utf-8', xml_declaration=True)
            print(f"Created: {front_dir / 'title.usx'}")


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert USX file to chunked files based on TOC structure')
    parser.add_argument('usx_file', help='Path to the input USX file')
    parser.add_argument('toc_file', help='Path to the TOC YAML file')
    parser.add_argument('output_dir', help='Path to the output directory')
    parser.add_argument('--book-code', default='REV', help='Book code for the USX file (default: REV)')
    parser.add_argument('--book-title', default='- Biblica® Open Vietnamese Contemporary Bible 2015 (Biblica® Thiên Ban Kinh Thánh Hiện Đại)', help='Book title for the USX file')
    
    args = parser.parse_args()
    
    # Create splitter and run
    splitter = USXSplitter(args.usx_file, args.toc_file, args.output_dir)
    splitter.run()


if __name__ == "__main__":
    main()
