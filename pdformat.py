import os
import re
import camelot
import pdfplumber
import numpy as np

from pdfminer.high_level import extract_text
from typing import List, Tuple, Union

from utils import (
    Rect, check_paragraph, merge_paragraph, transfer_to_image_coord, tracing_pdf_with_rect
)

ENABLE_CONCAT = False

class Formattor:
    def __init__(
        self, pdf_path,
        output_name: str = None,
        page_num: int | Union[List[int], Tuple[int]] = None, # from 1 to n
    ):
        self.pdf_path = pdf_path
        if not output_name:
            output_name = os.path.basename(pdf_path).split('.')[0] + '_out'
        self.output_name = output_name
        self.pdf_obj = None
        if isinstance(page_num, int):
            self.page_num = [page_num]
        elif page_num == None:
            self.page_num = None
        else:
            self.page_num = list(page_num)

    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return self

    def open(self):
        self.pdf_obj = pdfplumber.open(self.pdf_path)
        if self.page_num == None:
            self.page_num = list(range(1, len(self.pdf_obj.pages) + 1))
        return self
    
    def close(self):
        self.pdf_obj.close()
        return self
    
    def extract_text(self):
        if not self.pdf_obj:
            self.open()

        self.text = extract_text(pdf_path)
        with open('raw.temp', 'w', encoding='utf-8') as f:
            f.write(self.text)
        with open('raw.temp', 'r', encoding='utf-8') as f:
            self.lines = f.readlines()
        os.system("del -f raw.temp")

    def merge_text(self):
        self.line_tag = [""] * len(self.lines)
        iter_idx = 0
        for i in range(len(self.lines)):
            check_paragraph(self.lines, i, self.line_tag, [])

        from utils import is_one_block, is_word
        title = []
        pattern = r"^(\d(\.\d)?\.?)\s"
        for i, line in enumerate(self.lines):
            if re.match(pattern, line) and not is_one_block(line) and\
                is_word(line.split(' ')[1]):
                title.append((i, line))

        paras = merge_paragraph(self.lines, self.line_tag, title)

        if ENABLE_CONCAT:
            double_dict = {
                "ﬀ": "ff",
                "ﬁ": "fi",
                "ﬂ": "fl",
            }

            page_index = 0

            def conversion_bichar(text: str):
                for k, v in double_dict.items():
                    text = text.replace(k, v)
                return text
            
            def match_text(pat: str, text: str, flag: str = "re") -> int:
                pat = conversion_bichar(pat)
                print(pat)
                if flag == "re":
                    pat = re.escape(pat)
                    res = re.search(pat, text)
                    if res:
                        return res.start()
                    else:
                        return -1
                elif flag == "in":
                    return text.find(pat)

            failed_ids: int = -1
            end_flag = "err"
            changed_paras = [p_ for p_ in paras]

            words = []
            for page in self.pdf_obj.pages:
                words.append(page.extract_text(x_tolerance_ratio=0.135, keep_blank_chars=False, use_text_flow=True, layout=False))

            for i, para_ in enumerate(paras):
                if end_flag == "norm":
                    failed_ids = -1
                elif end_flag == "err" and failed_ids == -1:
                    failed_ids = i - 1

                pat = para_[0:13]

                sid = match_text(pat, words[page_index], flag="re")
                if sid == -1 and page_index < len(words) - 1:
                    sid = match_text(pat, words[page_index + 1], flag="re")
                    if not sid == -1:
                        page_index += 1
                    else:
                        sid = match_text(pat, words[page_index + 2], flag="re")
                        if not sid == -1:
                            page_index += 2
                        else:
                            print("no starting found")
                            print()
                            end_flag = "err"
                            continue

                pat = para_[-13:].strip()
                followed = " ".join(words[page_index][sid:].split("\n"))
                eid = match_text(pat, followed, flag="re")
                if eid == -1 and page_index < len(words) - 1:
                    print("no endding found")
                    print()
                    end_flag = "err"
                    continue
                rep_text = followed[:eid + len(conversion_bichar(pat))]
                rep_para = " ".join(rep_text.split("\n"))

                print()
                print(para_)
                print(rep_para)
                print()
                changed_paras[i] = rep_para
                end_flag = "norm"

            # too much error will callback to the previous page TODO
            # if failed_ids != -1:
            #     for i, para_ in paras[failed_ids:]:
            #         pass
            paras = changed_paras

        with open(self.output_name + ".txt", 'w', encoding='utf-8') as f:
            for p in paras:
                f.write(p + '\n')
                f.write('\n')

    def trace_parsing(self, path_dir: str = "tracing_results"): # the pdf image obj is draw with origin at upper left, so a transformation is needed
        for p in self.page_num:
            page = self.pdf_obj.pages[p - 1]
            im = page.to_image(resolution=100)
            rects, images, curves = page.rects, page.images, page.curves
            grids = []
            for rect in rects:
                x = rect['x0']
                y = rect['y0']
                w = rect['width']
                h = rect['height']
                grids.append((x, page.height-y-h, x+w, page.height-y))
            tracing_pdf_with_rect(im, grids, None, color="red") # rect is drawn from upper left corner to lower right corner

            grids = [(img['x0'], page.height-img['y1'], img['x1'], page.height-img['y0']) for img in images]
            im.draw_rects(grids, fill=None, stroke='blue', stroke_width=3)

            for curve in curves:
                x0 = curve['x0']
                y0 = curve['y0']
                x1 = curve['x1']
                y1 = curve['y1']
                im.draw_rect((x0, page.height-y1, x1, page.height-y0), stroke='green', stroke_width=3)
            if not os.path.exists(path_dir):
                os.makedirs(path_dir)
            im.save(os.path.join(path_dir, f"tracing_page_{p}.png"))


    def find_table_grid(self, page):
        page = self.pdf_obj.pages[page - 1]
        print("PAGE SIZE: ", page.width, page.height)
        rects = page.rects

        rect_list = []
        for rect in rects:
            x = rect['x0'] # this point is the bottom left corner, with origin at bottom left
            y = rect['y0']
            w = rect['width']
            h = rect['height']
            rect_list.append(Rect(x, y+h, x+w, y)) # we transform the point to the top left corner, with origin at bottom left
            print("RECT: ", x, y, w, h)
        
        rect_columns = []
        rect_rows = []
        tol = 5.
        for i, rect in enumerate(rect_list):
            if rect.w < tol and rect.h < tol:
                print(f"rect {i} is a point")
                continue
            elif rect.w < tol:
                rect_columns.append(rect)
            elif rect.h < tol:
                rect_rows.append(rect)
            else:
                print(f"rect {i} is a cell")
                continue
        
        COLUMNS = False
        if len(rect_columns) > len(rect_rows):
            COLUMNS = True

        if COLUMNS:
            choosen_rects = rect_columns
            choosen_rects = sorted(choosen_rects, key=lambda x: x.x0)
            grid_lines = [rect.w for rect in choosen_rects]
        else:
            choosen_rects = rect_rows
            choosen_rects = sorted(choosen_rects, key=lambda x: x.y0)
            grid_lines = [rect.h for rect in choosen_rects]
        
        grid_length = np.array(grid_lines)
        grid_matrix = grid_length[:, np.newaxis] - grid_length
        bool_matrix = grid_matrix < tol
        idx = np.argmax(bool_matrix.sum(axis=1))
        print(idx)
        valid_lines = np.where(bool_matrix[idx])[0].tolist()

        if COLUMNS:
            br_idx = max(valid_lines, key=lambda x: choosen_rects[x].x0)
            ul_idx = min(valid_lines, key=lambda x: choosen_rects[x].x0)
        else:
            br_idx = min(valid_lines, key=lambda x: choosen_rects[x].y0)
            ul_idx = max(valid_lines, key=lambda x: choosen_rects[x].y0)

        def trans(pos: list | tuple):
            if COLUMNS:
                pos = list(reversed(pos[0:4])) + list(pos[4:])
            return pos

        return trans((
            choosen_rects[ul_idx].x0 - 5,
            choosen_rects[ul_idx].y0 + 5,
            choosen_rects[br_idx].x1 + 5,
            choosen_rects[br_idx].y1 - 5,
            page.width,
            page.height,
        ))

    def got_table(self, page_str: str, table_areas: tuple|list|None = None):
        table_areas = "{}, {}, {}, {}".format(*[round(x) for x in table_areas])

        tables = camelot.read_pdf(
            pdf_path, flavor='stream', pages=page_str, flag_size=True, table_areas=[table_areas],
            # edge_tol = 500,
        )
        camelot.plot(tables[0], kind='contour').show()
        tables.export(self.output_name + '.md', f='markdown')

    def extract_table(self):
        for p in self.page_num:
            try:
                pos = self.find_table_grid(page=p)[0:4]
            except:
                print(f"Page {p} has no table")
                continue
            self.got_table(str(p), pos)
        

def find_files(dir, pattern):
    result = []
    for path, _, files in os.walk(dir):
        for file in files:
            if file.startswith(pattern):
                result.append(os.path.join(path, file))
    return result


if __name__ == "__main__":

    folder_path = "./papers/"
    for i, filename in enumerate(os.listdir(folder_path)):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            try:
                pdf_path = file_path

                ENABLE_CONCAT = False

                formattor = Formattor(pdf_path, output_name=f"./results/test-{i}", page_num=None)
                formattor.open()
                formattor.extract_text()
                formattor.merge_text()

                formattor.extract_table()
                formattor.close()
            except:
                continue


    r"""
    test code TODO
    """
    # from pdfminer.layout import LAParams
    # params = LAParams(word_margin=0.1)
    # text = extract_text(pdf_path, laparams = params)
    # with open('raw2.txt', 'w', encoding='utf-8') as f:
    #     f.write(text)


    # size_ = set()
    # for word in words:
    #     h = round((word["bottom"]-word["top"])*100)/100
    #     size_.add(h)
    #     if h == 7.17 or h== 7.2 or h==7.97 or h==8.82:
    #         im.draw_rect(word, fill=None, stroke='red', stroke_width=1)
    # im.show()
    # print(size_)

    # chars = page.chars
    # fonts = set()
    # for char in chars:
    #     fonts.add(char['fontname'])
    # print(fonts)

    # im = page.to_image(resolution=150)
    # for char in chars:
    #     if char['fontname'] == 'FKGKIH+AdvOT1efcda3b.B':
    #         im.draw_rect(char, fill=None, stroke='red', stroke_width=3)
    # im.show()

    # statistic the margin

    # chars = page.chars
    # print(len(chars))
    # size_ = set()
    # for char in chars:
    #     size_.add(char["height"])
    #     if char["height"] > 7.2:
    #         im.draw_rect(char, fill=None, stroke='red', stroke_width=1)
    #     else:
    #         im.draw_rect(char, fill=None, stroke='blue', stroke_width=1)

    # print(size_)
    # im.show()

    # tol = 1.
    # pre_char = None

    # im = page.to_image(resolution=150)

    # margin = dict()
    # for char in chars:
    #     if pre_char == None:
    #         pre_char = char
    #         continue

    #     if char['y0'] - pre_char['y0'] > tol:
    #         pre_char = char
    #         continue

    #     print("margin", char['x0'] - pre_char['x1'])

    #     margin.setdefault(round((char['x0'] - pre_char['x1'])*10)/10, 0)
    #     margin[round((char['x0'] - pre_char['x1'])*10)/10] += 1

    #     if round((char['x0'] - pre_char['x1'])*10)/10 > 1.:
    #         im.draw_rects([pre_char, char], fill=None, stroke='red', stroke_width=1)
    #     pre_char = char

    # margin_fi = {k: v for k, v in margin.items() if abs(k) < 10} # margin[k] > 10 and 

    # print(margin_fi)
    # im.show()

