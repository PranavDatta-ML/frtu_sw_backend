import re
from fpdf import FPDF

class PDFDoc(FPDF):
    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 12, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 9)
        self.set_xy(10, 3)
        self.cell(0, 6, 'FRTU Config Backend V1 - Backend Documentation', align='L')
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_fill_color(26, 26, 46)
        self.rect(0, 285, 210, 12, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', '', 8)
        self.set_xy(10, 287)
        self.cell(0, 5, f'Page {self.page_no()} | FRTU Config Backend V1 | 2026', align='L')
        self.set_text_color(0, 0, 0)


def clean(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    return text.strip()


def make_pdf(md_path, out_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    pdf = PDFDoc()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(15, 18, 15)

    i = 0
    while i < len(lines):
        raw = lines[i].rstrip('\n')
        stripped = raw.strip()

        # H1
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title = clean(stripped[2:])
            pdf.set_fill_color(26, 26, 46)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.ln(3)
            pdf.cell(0, 10, title, new_x='LMARGIN', new_y='NEXT', fill=True, align='C')
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

        # H2
        elif stripped.startswith('## '):
            title = clean(stripped[3:])
            pdf.set_fill_color(22, 33, 62)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.ln(4)
            pdf.cell(0, 8, title, new_x='LMARGIN', new_y='NEXT', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)

        # H3
        elif stripped.startswith('### '):
            title = clean(stripped[4:])
            pdf.set_text_color(15, 52, 96)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.ln(3)
            pdf.cell(0, 7, title, new_x='LMARGIN', new_y='NEXT')
            pdf.set_draw_color(15, 52, 96)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # H4
        elif stripped.startswith('#### '):
            title = clean(stripped[5:])
            pdf.set_text_color(60, 60, 60)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.ln(2)
            pdf.cell(0, 6, title, new_x='LMARGIN', new_y='NEXT')
            pdf.set_text_color(0, 0, 0)

        # Table
        elif stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1

            # parse rows
            rows = []
            for tl in table_lines:
                if re.match(r'^\|[\s\-\|:]+\|$', tl):
                    continue
                cells = [c.strip() for c in tl.strip('|').split('|')]
                rows.append(cells)

            if not rows:
                continue

            max_cols = max(len(r) for r in rows)
            col_w = (180) / max_cols

            # header row
            if rows:
                pdf.set_fill_color(26, 26, 46)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font('Helvetica', 'B', 8)
                for cell in rows[0]:
                    pdf.cell(col_w, 6, clean(cell)[:40], border=1, fill=True)
                pdf.ln()
                pdf.set_text_color(0, 0, 0)

                for r_idx, row in enumerate(rows[1:]):
                    if r_idx % 2 == 0:
                        pdf.set_fill_color(245, 245, 245)
                    else:
                        pdf.set_fill_color(255, 255, 255)
                    pdf.set_font('Helvetica', '', 8)
                    for cell in row:
                        pdf.cell(col_w, 5.5, clean(cell)[:50], border=1, fill=True)
                    pdf.ln()
            pdf.ln(2)
            continue

        # Code block
        elif stripped.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i].rstrip('\n'))
                i += 1
            pdf.set_fill_color(30, 30, 50)
            pdf.set_text_color(220, 220, 220)
            pdf.set_font('Courier', '', 8)
            pdf.ln(1)
            for cl in code_lines:
                cl_clean = cl.replace('\t', '    ')
                pdf.set_x(15)
                pdf.cell(0, 4.5, cl_clean[:100], new_x='LMARGIN', new_y='NEXT', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Blockquote
        elif stripped.startswith('>'):
            text = clean(stripped[1:].strip())
            pdf.set_fill_color(249, 249, 249)
            pdf.set_text_color(80, 80, 80)
            pdf.set_draw_color(26, 26, 46)
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_x(20)
            pdf.multi_cell(170, 5, text, border='L', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(0, 0, 0)

        # Bullet list
        elif stripped.startswith('- ') or stripped.startswith('* '):
            text = clean(stripped[2:])
            pdf.set_font('Helvetica', '', 10)
            pdf.set_x(20)
            pdf.cell(5, 5, chr(149), new_x='RIGHT', new_y='TOP')
            pdf.multi_cell(160, 5, text)

        # Numbered list
        elif re.match(r'^\d+\. ', stripped):
            text = clean(re.sub(r'^\d+\. ', '', stripped))
            pdf.set_font('Helvetica', '', 10)
            pdf.set_x(20)
            num = re.match(r'^(\d+)\. ', stripped).group(1)
            pdf.cell(8, 5, f'{num}.', new_x='RIGHT', new_y='TOP')
            pdf.multi_cell(157, 5, text)

        # HR
        elif stripped.startswith('---'):
            pdf.set_draw_color(180, 180, 180)
            pdf.ln(2)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(2)

        # Empty line
        elif stripped == '':
            pdf.ln(2)

        # Normal paragraph
        else:
            text = clean(stripped)
            if text:
                pdf.set_font('Helvetica', '', 10)
                pdf.multi_cell(0, 5, text)

        i += 1

    pdf.output(out_path)
    print(f'PDF saved: {out_path}')


if __name__ == '__main__':
    import os
    base = r'D:\KMP FRTU Configurator\frtu_config_backend_v1'
    make_pdf(
        os.path.join(base, 'BACKEND_DOCUMENTATION.md'),
        os.path.join(base, 'BACKEND_DOCUMENTATION.pdf')
    )
