import re
from pdfplumber.display import PageImage
from typing import List, Tuple, Union

class Rect:
    def __init__(self, x0, y0, x1, y1):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
    
    @property
    def w(self):
        return abs(self.x1 - self.x0)
    
    @property
    def h(self):
        return abs(self.y1 - self.y0)
    
    def get(self):
        return (self.x0, self.y0, self.x1, self.y1, self.w, self.h)

r"""
utils functions
"""
def equal(a, b):
    tol = 5.
    return abs(a-b) < tol

def transfer_to_image_coord(pos): # upper left coords, with origin at bottom left transformed to upper left
    h = pos[5]
    return (pos[0], h-pos[1], pos[2], h-pos[3])

def tracing_pdf_with_rect(im: PageImage, rects: List[Tuple] | Tuple, path="tracing.png", color='red'):
    im.draw_rects(rects, fill=None, stroke=color, stroke_width=3)
    if path==None:
        return im
    else:
        im.save(path)
        return None

pre_setting = { # TODO the tolerance in table findding, which should be implemented in the future
    'sentence_bound': 5,
}

def is_long_sentence(line, sentence_bound=6):
    words = line.strip().split(' ')
    return len(words) >= sentence_bound

def is_one_block(line):
    return len(line.strip().split(' ')) == 1

def is_few_block(line, block_bound=3, char_bound=5):
    if len(line.strip().split(' ')) > block_bound:
        return False
    for word in line.strip().split(' '):
        if len(word) > char_bound:
            return False
    return True

def is_word(line):
    return is_one_block(line) and line.strip().isalpha()

def is_number_block(line):
    return is_one_block(line) and any(char.isdigit() for char in line.strip())

def is_char(line):
    return len(line.strip()) == 1

def is_empty(line):
    return len(line.strip()) == 0

def register_long_sentence_length(line):
    return len(line.strip())

# TODO paragraph matching implemented in the future
figure_pattern = ['FIGURE', 'Figure', 'figure', 'fig', 'Fig']

order_pattern = r"[\[\(]?(\d+)[\]\)\.]?"

def check_paragraph(lines, iter_idx, line_tag, line_conf):
    i = iter_idx
    lt = line_tag

    if is_empty(lines[i]):
        lt[i] = 'empty'
        return
    
    if i == 0 or lt[i-1] == 'empty': # new sentence block
        if is_long_sentence(lines[i]):
            if is_empty(lines[i+1]):
                lt[i] = 'title'
            else:
                lt[i] = 'paragraph'
        elif is_few_block(lines[i]) or is_one_block(lines[i]):
            if is_long_sentence(lines[i+1]):
                lt[i] = 'paragraph'
            else:
                lt[i] = 'equation'
        else:
            lt[i] = '1-strange'

    elif lt[i-1] == 'paragraph':
        if is_long_sentence(lines[i]):
            lt[i] = 'paragraph'
        elif is_few_block(lines[i]) or is_one_block(lines[i]):
            if is_long_sentence(lines[i+1]) or is_empty(lines[i+1]):
                lt[i] = 'paragraph'
            else:
                lt[i] = 'equation'
        elif is_empty(lines[i+1]):
            lt[i] = 'paragraph'
        else:
            lt[i] = 'paragraph' # '2-strange' for a careful version
    
    elif lt[i-1] == 'equation':
        if is_long_sentence(lines[i]):
            lt[i] = 'paragraph'
        elif is_few_block(lines[i]) or is_one_block(lines[i]):
            lt[i] = 'equation'
        elif is_empty(lines[i+1]) or is_few_block(lines[i]) or is_one_block(lines[i]):
            lt[i] = 'equation'
        else:
            lt[i] = '3-strange'

    else:
        if is_long_sentence(lines[i]):
            if is_empty(lines[i+1]):
                lt[i] = 'title'
            else:
                lt[i] = 'paragraph'
        elif is_few_block(lines[i]) or is_one_block(lines[i]):
            if is_long_sentence(lines[i+1]):
                lt[i] = 'paragraph'
            else:
                lt[i] = 'equation'
        else:
            lt[i] = '4-strange'

def check_title(lines, iter_idx):
    pattern = r"^(\d(\.\d)?\.?)\s"
    results = re.match(pattern, lines[iter_idx])
    order = results.groups()[0].strip(".")
    return order.split(".")

def merge_paragraph(lines, line_tag, title):
    pattern = r"^(\[1\])"

    paragraphs = []
    para = ""
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            break
        if title and i > title[0][0]:
            paragraphs.append(title[0][1])
            title.pop(0)
        if not line_tag[i] == "paragraph":
            if para:
                paragraphs.append(para)
                para = ""
            continue

        para += line.strip() + " "

    return paragraphs