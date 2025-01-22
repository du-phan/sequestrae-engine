import json
import re


class BiocharExtractor:
    def __init__(self, markdown_content):
        self.markdown_content = markdown_content
