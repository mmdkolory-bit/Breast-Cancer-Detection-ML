from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Inches, Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'results' / 'figures'
TAB = ROOT / 'results' / 'tables'
OUT = ROOT / 'گزارش_پروژه_تشخیص_سرطان_سینه.docx'
FONT = 'Noto Sans Arabic'

summary = pd.read_csv(TAB / 'model_comparison_test.csv')
summary = summary.set_index('algorithm')
cv_files = {
    'Naive Bayes': 'sensitivity_naive_bayes.csv',
    'KNN': 'sensitivity_knn.csv',
    'Decision Tree': 'sensitivity_decision_tree.csv',
    'Random Forest': 'sensitivity_random_forest.csv',
    'SVM': 'sensitivity_svm.csv',
    'Logistic Regression': 'sensitivity_logistic_regression.csv',
    'ANN': 'sensitivity_ann.csv',
}
cv = {k: pd.read_csv(TAB / v) for k, v in cv_files.items()}


def set_run_font(run, size=10, bold=False, color=None, italic=False):
    run.font.name = FONT
    run._element.get_or_add_rPr().rFonts.set(qn('w:ascii'), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), FONT)
    run._element.get_or_add_rPr().rFonts.set(qn('w:cs'), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rtl = rpr.find(qn('w:rtl'))
    if rtl is None:
        rtl = OxmlElement('w:rtl'); rpr.append(rtl)
    rtl.set(qn('w:val'), '1')


def set_paragraph_rtl(p, align=WD_ALIGN_PARAGRAPH.RIGHT):
    p.alignment = align
    pPr = p._p.get_or_add_pPr()
    bidi = pPr.find(qn('w:bidi'))
    if bidi is None:
        bidi = OxmlElement('w:bidi'); pPr.append(bidi)
    bidi.set(qn('w:val'), '1')
    p.paragraph_format.space_after = Pt(3.5)
    p.paragraph_format.line_spacing = 1.04


def add_p(doc, text='', size=10, bold=False, align=WD_ALIGN_PARAGRAPH.RIGHT,
          color=None, space_before=0, space_after=5, italic=False):
    p = doc.add_paragraph()
    set_paragraph_rtl(p, align)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.04
    if text:
        r = p.add_run(text); set_run_font(r, size, bold, color, italic)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    set_paragraph_rtl(p)
    p.paragraph_format.space_before = Pt(5 if level == 1 else 3)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    set_run_font(r, 16 if level == 1 else 12, True, (31, 78, 121))
    return p


def add_bullet(doc, text, size=9.5):
    p = doc.add_paragraph()
    set_paragraph_rtl(p)
    p.paragraph_format.right_indent = Cm(0.35)
    p.paragraph_format.first_line_indent = Cm(-0.2)
    r = p.add_run('•  ' + text)
    set_run_font(r, size)
    return p


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn('w:shd'))
    if shd is None:
        shd = OxmlElement('w:shd'); tcPr.append(shd)
    shd.set(qn('w:fill'), fill)


def set_cell_text(cell, text, size=8.3, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ''
    p = cell.paragraphs[0]
    set_paragraph_rtl(p, align)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.space_before = Pt(1)
    r = p.add_run(str(text)); set_run_font(r, size, bold, color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def format_table(table, header=True, font_size=8.2):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    tblPr = table._tbl.tblPr
    bidi = OxmlElement('w:bidiVisual'); bidi.set(qn('w:val'), '1'); tblPr.append(bidi)
    for ri, row in enumerate(table.rows):
        for cell in row.cells:
            if ri == 0 and header:
                shade(cell, '1F4E79')
                for p in cell.paragraphs:
                    for r in p.runs:
                        set_run_font(r, font_size, True, (255,255,255))
            elif ri % 2 == 0:
                shade(cell, 'EEF3F8')
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def set_cell_widths(table, widths):
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)


def add_image(doc, path, width=6.45):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(3)
    p.add_run().add_picture(str(path), width=Inches(width))
    return p


def add_caption(doc, text):
    return add_p(doc, text, size=8.5, italic=True, color=(89,89,89), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)

def add_labelled_p(doc, label, text, size=8.7):
    p = doc.add_paragraph(); set_paragraph_rtl(p)
    p.paragraph_format.space_after = Pt(3); p.paragraph_format.line_spacing = 1.02
    r = p.add_run(label); set_run_font(r, size, True, (31,78,121))
    r = p.add_run(text); set_run_font(r, size)
    return p


def add_page_field(paragraph):
    r = paragraph.add_run('')
    fldChar1 = OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText'); instrText.set(qn('xml:space'), 'preserve'); instrText.text = ' PAGE '
    fldChar2 = OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'), 'end')
    r._r.append(fldChar1); r._r.append(instrText); r._r.append(fldChar2)
    set_run_font(r, 8, False, (100,100,100))


def fmt(v):
    return f'{float(v):.3f}'


def metric_line(name):
    r = summary.loc[name]
    return (f"در مجموعهٔ آزمون، Accuracy برابر {fmt(r.test_accuracy)}، Precision برابر {fmt(r.test_precision)}، "
            f"Sensitivity برابر {fmt(r.test_sensitivity)}، Specificity برابر {fmt(r.test_specificity)}، "
            f"F1 برابر {fmt(r.test_f1)} و ROC-AUC برابر {fmt(r.test_roc_auc)} به دست آمد.")


def selected_row(name):
    return summary.loc[name]


doc = Document()
sec = doc.sections[0]
sec.top_margin = Cm(1.35); sec.bottom_margin = Cm(1.35)
sec.left_margin = Cm(1.7); sec.right_margin = Cm(1.7)
sec.header_distance = Cm(0.65); sec.footer_distance = Cm(0.65)

# Default styles and language.
for style_name in ['Normal', 'Body Text', 'Caption']:
    style = doc.styles[style_name]
    style.font.name = FONT; style.font.size = Pt(10)
    style._element.rPr.rFonts.set(qn('w:ascii'), FONT)
    style._element.rPr.rFonts.set(qn('w:hAnsi'), FONT)
    style._element.rPr.rFonts.set(qn('w:cs'), FONT)

# Header / footer.
header = sec.header.paragraphs[0]
set_paragraph_rtl(header, WD_ALIGN_PARAGRAPH.RIGHT)
r = header.add_run('پروژه ۱ | تشخیص سرطان سینه با یادگیری ماشین')
set_run_font(r, 8, True, (89,89,89))
footer = sec.footer.paragraphs[0]
set_paragraph_rtl(footer, WD_ALIGN_PARAGRAPH.CENTER)
r = footer.add_run('گزارش آزمایشگاهی  |  صفحه '); set_run_font(r, 8, False, (100,100,100))
add_page_field(footer)

# Cover
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(95); p.paragraph_format.space_after = Pt(15)
r = p.add_run('گزارش پروژه ۱'); set_run_font(r, 25, True, (31,78,121))
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('تشخیص سرطان سینه با الگوریتم‌های یادگیری ماشین'); set_run_font(r, 21, True)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Breast Cancer Classification | WDBC'); set_run_font(r, 14, True, (89,89,89))
add_p(doc, 'پیاده‌سازی و مقایسهٔ هفت الگوریتم مطابق اسلاید ۱۷۸', size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=26, space_after=30)
add_p(doc, 'تهیه‌شده برای ارائه به آقای عباسی', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
add_p(doc, 'تاریخ اجرا: ۱۰ نوامبر ۲۰۲۶', size=10, color=(89,89,89), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=45)
add_p(doc, 'هشدار: این پروژه فقط برای آموزش و پژوهش است و نباید برای تشخیص پزشکی یا تصمیم درمانی استفاده شود.', size=10, bold=True, color=(156,0,6), align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20, space_after=20)
doc.add_page_break()

# Executive summary
add_heading(doc, '۱. خلاصهٔ اجرایی', 1)
add_p(doc, 'هدف این پروژه، ساخت یک فرایند قابل‌بازتولید برای تشخیص دودویی تومور پستان از روی ویژگی‌های عددی مجموعه‌دادهٔ WDBC و مقایسهٔ هفت الگوریتم معرفی‌شده در اسلاید ۱۷۸ است. کلاس مثبت در تمام محاسبات «بدخیم» تعریف شده است؛ بنابراین حساسیت (Sensitivity) نشان می‌دهد چه نسبتی از نمونه‌های واقعاً بدخیم شناسایی شده‌اند.')
add_p(doc, 'برای هر الگوریتم شش مقدار از پارامتر اصلی بررسی شد. نمودار هر بخش شش خط دارد: Accuracy، Precision، Sensitivity/Recall، F1-score، Specificity و ROC-AUC. هر نقطه، میانگین اعتبارسنجی متقاطع پنج‌بخشی روی دادهٔ آموزش است. در نتیجه نمودارها اثر تغییر پارامتر را نشان می‌دهند و با نتیجهٔ نهاییِ مجموعهٔ آزمون اشتباه گرفته نمی‌شوند.')
add_p(doc, 'برای جلوگیری از نشت اطلاعات، ابتدا ۲۰٪ داده به‌صورت طبقه‌بندی‌شده برای آزمون نهایی جدا شد. انتخاب ویژگی و استانداردسازی داخل Pipeline و فقط با دادهٔ آموزش هر fold انجام شدند. تنظیم نهایی نیز با بیشترین حساسیتِ اعتبارسنجی انتخاب شد؛ در تساوی، F1 و سپس ROC-AUC ملاک قرار گرفتند.')
add_heading(doc, 'نتیجهٔ اصلی', 2)
add_p(doc, 'در آزمون نگه‌داشته‌شده، SVM بیشترین حساسیت را با مقدار ۰٫۹۷۶ به دست آورد و فقط یک نمونهٔ بدخیم را از دست داد. Logistic Regression نیز Accuracy برابر ۰٫۹۷۴ و ROC-AUC برابر ۰٫۹۹۶ داشت. Random Forest هیچ نمونهٔ خوش‌خیم را به‌اشتباه بدخیم اعلام نکرد (Specificity=1.000)، اما سه نمونهٔ بدخیم را از دست داد. بنابراین انتخاب مدل به اولویت میان خطای منفی کاذب و مثبت کاذب وابسته است.')
add_p(doc, 'این نتیجه‌ها فقط مربوط به یک تقسیم مشخص از یک مجموعه‌دادهٔ آموزشی هستند. برای استفادهٔ واقعی، دادهٔ مستقل، ارزیابی خارجی، کالیبراسیون و بررسی بالینی/قانونی لازم است.', size=9.5, bold=True, color=(156,0,6))
doc.add_page_break()

# Dataset and methodology
add_heading(doc, '۲. داده‌ها و آماده‌سازی', 1)
add_p(doc, 'مجموعه‌دادهٔ Breast Cancer Wisconsin (Diagnostic) شامل ۵۶۹ نمونه و ۳۰ ویژگی حقیقی است: ۲۱۲ نمونه بدخیم و ۳۵۷ نمونه خوش‌خیم. ویژگی‌ها از تصویر دیجیتال نمونهٔ آسپیراسیون با سوزن ظریف (FNA) استخراج شده‌اند و توصیفگرهای شکل و بافت هستهٔ سلول را بیان می‌کنند. هر یک از ۱۰ توصیفگر اصلی در سه شکل میانگین، خطای معیار و مقدار بدترین/بزرگ‌ترین گزارش شده است؛ در مجموع ۳۰ ویژگی حاصل می‌شود.')
add_p(doc, 'نکتهٔ مهم دربارهٔ مرحلهٔ Feature Extraction: در این پروژه تصویر خام پزشکی پردازش نمی‌شود. ویژگی‌های ۳۰گانه از قبل در نسخهٔ استاندارد WDBC استخراج شده‌اند. کاری که این پیاده‌سازی اضافه می‌کند «انتخاب ویژگی» است: با آزمون ANOVA و SelectKBest، تعداد ۲۰ ویژگی از ۳۰ ویژگی انتخاب می‌شود. این انتخاب درون هر fold انجام می‌شود تا اطلاعات fold ارزیابی وارد آموزش نشود.')
add_heading(doc, 'مراحل فرایند', 2)
add_bullet(doc, 'دادهٔ ورودی: ۳۰ ویژگی عددی و برچسب خوش‌خیم/بدخیم؛ در دادهٔ همراه این پروژه مقدار گمشده‌ای گزارش نشده است.')
add_bullet(doc, 'تقسیم داده: ۸۰٪ آموزش (۴۵۵ نمونه) و ۲۰٪ آزمون (۱۱۴ نمونه)، با حفظ نسبت کلاس‌ها و random_state=42.')
add_bullet(doc, 'اعتبارسنجی: StratifiedKFold با پنج بخش فقط روی ۴۵۵ نمونهٔ آموزش؛ هر تنظیم پارامتر در پنج fold ارزیابی شد.')
add_bullet(doc, 'پیش‌پردازش: انتخاب ۲۰ ویژگی درون Pipeline؛ سپس StandardScaler برای الگوریتم‌های حساس به مقیاس (NB، KNN، SVM، Logistic Regression و ANN). درخت تصمیم و جنگل تصادفی به استانداردسازی نیاز ندارند.')
add_bullet(doc, 'آموزش و ارزیابی: پس از انتخاب پارامتر، مدل روی تمام بخش آموزش fit و فقط یک‌بار روی ۱۱۴ نمونهٔ آزمون ارزیابی شد.')
add_heading(doc, 'معنی کلاس مثبت و معیارها', 2)
add_p(doc, 'TP: بدخیمِ درست شناسایی‌شده؛ FN: بدخیمِ ازدست‌رفته؛ TN: خوش‌خیمِ درست شناسایی‌شده؛ FP: خوش‌خیمِ اشتباه اعلام‌شده به‌عنوان بدخیم. Accuracy سهم کل پیش‌بینی‌های درست؛ Precision سهم پیش‌بینی‌های بدخیم که واقعاً بدخیم‌اند؛ Sensitivity=TP/(TP+FN)؛ Specificity=TN/(TN+FP)؛ F1 میانگین هارمونیک Precision و Sensitivity؛ و ROC-AUC توانایی رتبه‌بندی دو کلاس در آستانه‌های مختلف است.')
add_p(doc, 'از آنجا که از دست دادن نمونهٔ بدخیم در این مسئله هزینهٔ بالایی دارد، معیار اصلی انتخاب پارامتر Sensitivity در نظر گرفته شد. این انتخاب، هزینهٔ خطاهای دیگر را حذف نمی‌کند و صرفاً اولویت تحلیل را مشخص می‌کند.', size=9.5)
doc.add_page_break()

# Overall performance
add_heading(doc, '۳. مقایسهٔ نهایی هفت الگوریتم روی دادهٔ آزمون', 1)
add_p(doc, 'جدول زیر عملکرد مدل‌هایی را نشان می‌دهد که پارامتر آن‌ها فقط با اعتبارسنجی پنج‌بخشیِ دادهٔ آموزش انتخاب شده است. همهٔ اعداد جدول مربوط به مجموعهٔ آزمونِ کنارگذاشته‌شده هستند.')
cols = ['الگوریتم', 'Accuracy', 'Precision', 'Sensitivity', 'Specificity', 'F1', 'AUC']
t = doc.add_table(rows=1, cols=len(cols))
for i, c in enumerate(cols): set_cell_text(t.rows[0].cells[i], c, 7.0, True, (255,255,255))
for name in ['Naive Bayes','KNN','Decision Tree','Random Forest','SVM','Logistic Regression','ANN']:
    r = summary.loc[name]
    cells = t.add_row().cells
    vals = [name, fmt(r.test_accuracy), fmt(r.test_precision), fmt(r.test_sensitivity), fmt(r.test_specificity), fmt(r.test_f1), fmt(r.test_roc_auc)]
    for i, v in enumerate(vals): set_cell_text(cells[i], v, 7.1, i==0)
format_table(t, True, 7.0)
set_cell_widths(t, [1.55,0.78,0.78,0.88,0.88,0.62,0.62])
add_caption(doc, 'جدول ۱ ـ عملکرد مدل‌ها در آزمون نگه‌داشته‌شده؛ کلاس مثبت = بدخیم')
add_image(doc, FIG / 'test_model_comparison.png', 5.85)
add_caption(doc, 'شکل ۱ ـ مقایسهٔ معیارهای اصلی در مجموعهٔ آزمون؛ این نمودار با نمودارهای تنظیم پارامتر متفاوت است.')
add_p(doc, 'برداشت: SVM با حساسیت ۰٫۹۷۶ بهترین نرخ کشف بدخیمی را در این تقسیم آزمون داشت (۴۱ مورد از ۴۲ مورد بدخیم). Logistic Regression نیز حساسیت ۰٫۹۵۲، Specificity برابر ۰٫۹۸۶ و AUC برابر ۰٫۹۹۶ داشت. Random Forest با Specificity برابر ۱٫۰۰۰ هیچ FP نداشت، اما حساسیت آن ۰٫۹۲۹ بود. Decision Tree در این اجرا ضعیف‌ترین AUC و Accuracy را ثبت کرد؛ این رفتار با نوسان بالاتر یک درخت منفرد نسبت به مدل‌های تجمیعی سازگار است.')

# Per-algorithm content
sections = [
    {
        'name':'Naive Bayes', 'fa':'۴. الگوریتم Naive Bayes', 'param':'var_smoothing', 'chosen':'1e-12',
        'role':'پارامتر var_smoothing مقدار کوچکی به واریانس ویژگی‌ها اضافه می‌کند تا از تقسیم بر واریانس بسیار کوچک و ناپایداری محاسباتی جلوگیری شود. در این آزمایش ویژگی‌ها استاندارد شده‌اند و شش مقدار ۱۰⁻¹² تا ۱۰⁻⁷ در مقایسه با واریانس ویژگی‌های مقیاس‌شده بسیار کوچک‌اند.',
        'reading':'هر شش خط تقریباً کاملاً افقی و روی هم افتاده‌اند؛ بنابراین تغییر این بازه از var_smoothing روی پیش‌بینی‌های اعتبارسنجی اثر قابل‌اندازه‌گیری نداشته است. این به معنی بی‌اثر بودن همیشگی پارامتر نیست؛ فقط نشان می‌دهد بازهٔ آزموده‌شده برای این داده و پیش‌پردازش، بیش از حد کوچک بوده است.',
        'trade':'چون معیارهای شش تنظیم برابر یا بسیار نزدیک بوده‌اند، مقدار 1e-12 به‌عنوان اولین تنظیمِ دارای بیشترین حساسیت انتخاب شده است؛ نباید آن را برندهٔ قطعی و معنادار دانست. برای مشاهدهٔ اثر واقعی‌تر می‌توان در آزمایش تکمیلی بازهٔ بزرگ‌تری را بررسی کرد، اما لازم است پایداری و افت عملکرد نیز کنترل شود.',
        'result':'در آزمون، حساسیت ۰٫۸۵۷ و Specificity برابر ۰٫۹۸۶ است؛ یعنی ۳۶ مورد از ۴۲ بدخیم شناسایی و ۶ مورد از دست رفته‌اند. این مدل در این تنظیم، نمونه‌های خوش‌خیم را خوب تشخیص می‌دهد اما از نظر کشف بدخیمی به‌اندازهٔ SVM و Logistic Regression قوی نیست.'
    },
    {
        'name':'KNN', 'fa':'۵. الگوریتم K-Nearest Neighbors (KNN)', 'param':'n_neighbors = k', 'chosen':'3',
        'role':'پارامتر k تعداد همسایه‌هایی را تعیین می‌کند که رأی آن‌ها برای طبقه‌بندی نمونه استفاده می‌شود. در این پروژه رأی‌دهی distance-weighted و فاصلهٔ Minkowski با p=2 (فاصلهٔ اقلیدسی) ثابت شده است؛ بنابراین همسایه‌های نزدیک‌تر وزن بیشتری دارند.',
        'reading':'در k=1 مدل به نمونه‌های بسیار محلی وابسته است و می‌تواند به نویز حساس باشد. با افزایش k تا ۳، Accuracy و F1 بهتر می‌شوند و حساسیت به بیشینهٔ حدود ۰٫۹۳۵ می‌رسد. از kهای بزرگ‌تر، خطوط حساسیت و F1 اندکی افت می‌کنند؛ زیرا همسایه‌های دورتر مرز محلی کلاس‌ها را هموار و گاهی مبهم می‌کنند. در مقابل ROC-AUC تا kهای بزرگ‌تر اندکی رشد می‌کند، یعنی رتبه‌بندی احتمال/امتیازها لزوماً با معیار آستانه‌ایِ پیش‌بینی یکسان حرکت نمی‌کند.',
        'trade':'k کوچک واریانس و بیش‌برازش محلی را بالا می‌برد؛ k بزرگ‌تر بایاس را افزایش می‌دهد و ممکن است مرزهای نزدیک را محو کند. k=3 با حساسیت و F1 بالا انتخاب شد. استانداردسازی در KNN ضروری است، چون در غیر این صورت ویژگی‌هایی با دامنهٔ عددی بزرگ‌تر می‌توانند فاصله را تحت سلطهٔ خود بگیرند.',
        'result':'در آزمون، Accuracy برابر ۰٫۹۴۷ و حساسیت ۰٫۸۸۱ است؛ ۳۷ مورد از ۴۲ بدخیم شناسایی شدند. عملکرد مناسب است، اما پنج مورد بدخیم از دست رفته‌اند و SVM/Logistic Regression در این تقسیم بهتر عمل کرده‌اند.'
    },
    {
        'name':'Decision Tree', 'fa':'۶. الگوریتم Decision Tree', 'param':'max_depth', 'chosen':'8',
        'role':'پارامتر max_depth حداکثر عمق درخت و در عمل میزان پیچیدگی آن را کنترل می‌کند. عمق کم تعداد پرسش‌ها و مرزهای تصمیم را محدود می‌کند؛ عمق زیاد اجازه می‌دهد الگوهای جزئی‌تر و تعاملات بیشتری میان ویژگی‌ها آموخته شوند.',
        'reading':'در عمق ۱ حساسیت پایین‌تر است؛ درخت ساده است و بخشی از الگوی جداسازی را نمی‌آموزد (کم‌برازش). افزایش عمق تا ۶ و ۸ عموماً حساسیت را بالا می‌برد؛ در عمق ۸ بیشترین حساسیت اعتبارسنجی در این شبکهٔ آزمایش ثبت شد. با این حال بعضی معیارها در عمق ۶ اندکی بهترند؛ برای نمونه F1 در عمق ۶ حدود ۰٫۹۰۸ و در عمق ۸ حدود ۰٫۹۰۷ است. پس افزایش عمق همهٔ معیارها را هم‌زمان بهتر نمی‌کند.',
        'trade':'عمق بیشتر می‌تواند واریانس و بیش‌برازش را بالا ببرد، به‌ویژه در مجموعه‌دادهٔ کوچک. انتخاب عمق ۸ ناشی از اولویتِ حساسیت بوده و با معیار F1/AUC انتخاب متفاوتی ممکن است. محدودسازی با min_samples_leaf، min_samples_split یا pruning در آزمایش تکمیلی می‌تواند پایداری را بهتر کند.',
        'result':'در آزمون Accuracy برابر ۰٫۹۰۴، حساسیت ۰٫۸۵۷ و AUC برابر ۰٫۸۹۴ به دست آمد. شش نمونهٔ بدخیم از دست رفتند. درخت منفرد نسبت به Random Forest نوسان بیشتری دارد و نتیجهٔ این آزمایش نیز نشان می‌دهد تجمیع چند درخت عملکرد آزمون را بهتر کرده است.'
    },
    {
        'name':'Random Forest', 'fa':'۷. الگوریتم Random Forest', 'param':'n_estimators', 'chosen':'25',
        'role':'پارامتر n_estimators تعداد درخت‌هایی را تعیین می‌کند که در جنگل ساخته و رأی آن‌ها تجمیع می‌شود. افزایش تعداد درخت‌ها معمولاً نوسان ناشی از یک درخت را کاهش می‌دهد، اما هزینهٔ محاسباتی را نیز بالا می‌برد.',
        'reading':'از ۱۰ به ۲۵ درخت، حساسیت و F1 میانگین اعتبارسنجی بهتر می‌شوند؛ در ۲۵ درخت حساسیت حدود ۰٫۹۴۷ و F1 حدود ۰٫۹۵۰ است. بعد از آن خطوط تقریباً به حالت اشباع می‌رسند و تغییرات کوچک میان ۵۰ تا ۲۰۰ درخت دیده می‌شود. این نوسان کوچک در دادهٔ محدود طبیعی است و به زیرنمونه‌گیری تصادفی و ساختار درخت‌ها وابسته است.',
        'trade':'تعداد درخت بیشتر الزاماً باعث افزایش بزرگ دقت نمی‌شود؛ پس از رسیدن به پایداری، سود نهایی کم و زمان اجرا بیشتر می‌شود. در این آزمایش ۲۵ درخت بر اساس حساسیت و سپس F1 انتخاب شده است. مقدار random_state ثابت شده تا مقایسه بازتولیدپذیرتر باشد.',
        'result':'در آزمون Accuracy برابر ۰٫۹۷۴، Precision برابر ۱٫۰۰۰ و Specificity برابر ۱٫۰۰۰ شد؛ یعنی هیچ خوش‌خیمی به‌اشتباه بدخیم اعلام نشد. در عوض حساسیت ۰٫۹۲۹ است و سه بدخیمی از دست رفته‌اند. این نمونه‌ای از مبادلهٔ میان FP و FN است.'
    },
    {
        'name':'SVM', 'fa':'۸. الگوریتم Support Vector Machine (SVM)', 'param':'C', 'chosen':'100',
        'role':'پارامتر C جریمهٔ خطا را کنترل می‌کند و معکوسِ شدت منظم‌سازی است: C کوچک‌تر مرز ساده‌تر و منظم‌سازی قوی‌تر ایجاد می‌کند؛ C بزرگ‌تر مدل را وادار می‌کند خطاهای آموزشی را بیشتر جبران کند و ممکن است مرز پیچیده‌تری بسازد. در این آزمایش هستهٔ RBF و gamma=scale ثابت هستند.',
        'reading':'در C=0.01، Accuracy حدود ۰٫۶۲۶، Specificity برابر ۱ و حساسیت/Precision/F1 برابر صفر است. مدل عملاً همهٔ نمونه‌ها را خوش‌خیم پیش‌بینی کرده؛ در نتیجه هیچ خوش‌خیمی را اشتباه بدخیم نمی‌خواند اما تمام بدخیمی‌ها را از دست می‌دهد. با افزایش C به ۰٫۱ و ۱، خطوط حساسیت، F1 و Accuracy جهش می‌کنند. برای Cهای بالاتر حساسیت کمی بهتر می‌شود، اما Precision و Specificity اندکی افت می‌کنند.',
        'trade':'این نمودار نشان می‌دهد تکیه بر Accuracy یا Specificity به‌تنهایی خطرناک است: C=0.01 ویژگی کامل دارد، اما برای هدف تشخیص بدخیمی کاملاً نامناسب است. C=100 و 1000 حساسیت اعتبارسنجی مشابه دارند، ولی F1 در C=100 اندکی بهتر است؛ به همین دلیل C=100 انتخاب شده است. استانداردسازی برای SVM مهم است تا فاصله‌ها و حاشیهٔ تصمیم تحت سلطهٔ مقیاس یک ویژگی قرار نگیرند.',
        'result':'در آزمون، حساسیت ۰٫۹۷۶ است؛ ۴۱ مورد از ۴۲ بدخیم پیدا شدند و فقط یک FN وجود دارد. Accuracy برابر ۰٫۹۷۴ و Specificity برابر ۰٫۹۷۲ است. این مدل در این تقسیم، بهترین حساسیت آزمون را داشته است.'
    },
    {
        'name':'Logistic Regression', 'fa':'۹. الگوریتم Logistic Regression', 'param':'C', 'chosen':'100',
        'role':'در Logistic Regression، پارامتر C معکوس شدت منظم‌سازی L2 است. C کوچک ضرایب را بیشتر محدود می‌کند و از پیچیدگی جلوگیری می‌کند؛ C بزرگ اجازه می‌دهد ضرایب بزرگ‌تر و مرز متناسب‌تری با داده آموزش داده شود.',
        'reading':'در Cهای بسیار کوچک (۰٫۰۰۱ و ۰٫۰۱) مدل محدودتر است. با رسیدن C به ۰٫۱ و ۱، Accuracy، Precision، F1 و AUC بالا می‌روند و به ناحیهٔ نسبتاً پایدار می‌رسند. در C=100 حساسیت به حدود ۰٫۹۴۷ در اعتبارسنجی می‌رسد، اما Specificity و Precision کمی پایین‌تر می‌آیند؛ یعنی مدل برای کشف بدخیمی‌های بیشتر، اندکی مثبت کاذب بیشتر می‌پذیرد.',
        'trade':'نمودار در بخش C=0.1 تا ۱۰ نشان‌دهندهٔ ناحیهٔ عملکرد پایدار است؛ تغییر C در این ناحیه اثر ناگهانی ندارد. C=100 به دلیل بیشترین حساسیت انتخاب شد، نه به این معنا که از نظر همهٔ معیارها بهترین است. استفاده از StandardScaler برای هم‌مقیاس شدن ضرایب و عملکرد منظم‌سازی اهمیت دارد.',
        'result':'در آزمون Accuracy=۰٫۹۷۴، Precision=۰٫۹۷۶، Sensitivity=۰٫۹۵۲، Specificity=۰٫۹۸۶ و AUC=۰٫۹۹۶ است. از ۴۲ نمونهٔ بدخیم، ۴۰ مورد شناسایی شدند و دو مورد از دست رفتند.'
    },
    {
        'name':'ANN', 'fa':'۱۰. شبکهٔ عصبی مصنوعی (ANN / MLP)', 'param':'hidden_layer_sizes', 'chosen':'(64, 32)',
        'role':'پارامتر hidden_layer_sizes تعداد نورون‌ها و لایه‌های پنهان را مشخص می‌کند. برای نمونه (64,32) یعنی دو لایهٔ پنهان با ۶۴ و ۳۲ نورون. معماری کوچک ظرفیت محدودی دارد؛ معماری بزرگ‌تر می‌تواند الگوهای غیرخطی و تعامل پیچیده‌تری را یاد بگیرد.',
        'reading':'با افزایش ظرفیت از (8) به (16,8) عملکرد کلی بهتر می‌شود. معماری (32,16) Precision و Specificity بسیار بالایی دارد، در حالی که (64,32) بیشترین حساسیت اعتبارسنجی را ثبت می‌کند. افت نسبی Precision و Specificity در مدل بزرگ‌تر نشان می‌دهد مدل بیشتری از نمونه‌ها را بدخیم اعلام می‌کند تا FN کمتر شود؛ در عوض ممکن است FP افزایش یابد.',
        'trade':'شبکهٔ بزرگ‌تر پارامترهای بیشتری دارد و روی ۴۵۵ نمونهٔ آموزش می‌تواند بیش‌برازش کند. برای کاهش این خطر، ویژگی‌ها استاندارد شدند، alpha=0.0001 به‌عنوان منظم‌سازی L2، early_stopping=True و اعتبارسنجی داخلی توقف زودهنگام استفاده شد. معماری (64,32) با اولویت حساسیت انتخاب شد؛ نتیجهٔ آن باید با احتیاط و روی دادهٔ مستقل دوباره بررسی شود.',
        'result':'در آزمون Accuracy=۰٫۹۵۶، Sensitivity=۰٫۹۲۹ و AUC=۰٫۹۹۶ است. ۳۹ مورد از ۴۲ بدخیم شناسایی و سه مورد از دست رفتند. AUC بالا نشان می‌دهد امتیازهای مدل رتبه‌بندی خوبی دارند، اما در آستانهٔ پیش‌فرض، حساسیت آن از SVM پایین‌تر است.'
    },
]

for secdata in sections:
    doc.add_page_break()
    add_heading(doc, secdata['fa'], 1)
    sr = selected_row(secdata['name'])
    add_p(doc, f"پارامتر بررسی‌شده: {secdata['param']}  |  مقدار انتخاب‌شده با اعتبارسنجی: {secdata['chosen']}  |  حساسیت CV در تنظیم انتخابی: {fmt(sr.cv_sensitivity)}  |  F1 در CV: {fmt(sr.cv_f1)}", size=9.3, bold=True, color=(31,78,121))
    safe = secdata['name'].lower().replace(' ', '_')
    add_image(doc, FIG / f'sensitivity_{safe}.png', 5.85)
    add_caption(doc, 'شش خط: Accuracy، Precision، Sensitivity، F1، Specificity و ROC-AUC؛ هر نقطه میانگین پنج fold است.')
    add_labelled_p(doc, 'اثر پارامتر: ', secdata['role'], 8.7)
    add_labelled_p(doc, 'علت شکل خطوط: ', secdata['reading'], 8.7)
    add_labelled_p(doc, 'تفسیر و انتخاب: ', secdata['trade'], 8.7)
    add_labelled_p(doc, 'نتیجهٔ آزمون: ', secdata['result'], 8.7)

# Confusion matrices and final conclusion
doc.add_page_break()
add_heading(doc, '۱۱. تحلیل خطاها و ماتریس‌های اغتشاش', 1)
add_p(doc, 'ماتریس اغتشاش تفکیک می‌کند چند نمونهٔ خوش‌خیم و بدخیم درست یا اشتباه طبقه‌بندی شده‌اند. ترتیب محورهای شکل زیر در هر ماتریس یکسان است: ردیف‌ها کلاس واقعی و ستون‌ها کلاس پیش‌بینی‌شده هستند؛ در هر دو محور ابتدا Benign و سپس Malignant آمده است.')
add_image(doc, FIG / 'confusion_matrices_test.png', 5.8)
add_caption(doc, 'شکل ـ ماتریس اغتشاش هفت مدل بر روی همان ۱۱۴ نمونهٔ آزمون')
add_p(doc, 'SVM با TN=70، FP=2، FN=1 و TP=41 کمترین FN را داشت. Logistic Regression با FN=2 و FP=1 تعادل خوبی نشان داد. Random Forest با FP=0 هیچ خوش‌خیمی را اشتباه بدخیم اعلام نکرد، اما FN=3 داشت. Naive Bayes و Decision Tree هر کدام ۶ FN داشتند. بنابراین تعداد FN باید در کنار Accuracy و سایر معیارها دیده شود.', size=8.8)
add_heading(doc, 'جمع‌بندی', 2)
add_p(doc, 'در این آزمایش SVM (C=100) از نظر حساسیت آزمون بهترین بود؛ Logistic Regression (C=100) نیز Accuracy و AUC بالایی داشت و Random Forest (۲۵ درخت) بهترین Specificity را ثبت کرد. یک الگوریتم در همهٔ معیارها برنده نیست؛ انتخاب نهایی باید بر اساس هزینهٔ FN و FP و اعتبارسنجی مستقل باشد.', size=8.8)
add_p(doc, 'محدودیت: نتیجه به یک تقسیم train/test و یک مجموعه‌داده محدود است؛ برای نتیجه‌گیری محکم‌تر، اعتبارسنجی تکرارشونده و آزمون خارجی لازم است. هیچ‌یک از مدل‌ها ابزار تشخیص بالینی نیستند.', size=8.8, bold=True, color=(156,0,6))

# Reproducibility and references
doc.add_page_break()
add_heading(doc, '۱۲. بازتولید آزمایش و ساختار کد', 1)
add_p(doc, 'کد کامل در مخزن پروژه قرار دارد. فایل src/train_models.py دادهٔ استاندارد را بارگذاری می‌کند، تقسیم طبقه‌بندی‌شده را می‌سازد، هفت مدل و شش مقدار پارامتر هر مدل را با اعتبارسنجی پنج‌بخشی می‌سنجد، مدل نهایی را روی بخش آموزش برازش می‌کند و گزارش آزمون، نمودارها و فایل مدل‌ها را ذخیره می‌کند.')
add_p(doc, 'برای اجرای مجدد، در پوشهٔ اصلی پروژه دستورهای زیر اجرا شوند:')
code = doc.add_paragraph(); code.alignment = WD_ALIGN_PARAGRAPH.LEFT
for line in ['python -m venv .venv', 'pip install -r requirements.txt', 'python src/train_models.py']:
    rr = code.add_run(line + '\n'); rr.font.name = 'DejaVu Sans Mono'; rr.font.size = Pt(9)
add_p(doc, 'خروجی‌های تصویری در results/figures، جدول‌ها در results/tables، مدل‌های نهایی در models و تنظیمات اجرا در results/run_metadata.json ذخیره می‌شوند. نسخهٔ Word حاضر نیز در ریشهٔ مخزن قرار دارد.')
add_heading(doc, 'منابع', 1)
refs = [
    'UCI Machine Learning Repository. Breast Cancer Wisconsin (Diagnostic). DOI: 10.24432/C5DW2B. https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic',
    'scikit-learn Developers. load_breast_cancer dataset documentation. https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_breast_cancer.html',
    'Street, W., Wolberg, W., & Mangasarian, O. (1993). Nuclear feature extraction for breast tumor diagnosis. Electronic Imaging.',
    'scikit-learn Developers. Supervised learning, preprocessing, model selection, and classifier API documentation. https://scikit-learn.org/stable/user_guide.html',
]
for i, ref in enumerate(refs, 1):
    add_p(doc, f'{i}. {ref}', size=8.8)
add_p(doc, 'یادداشت داده: نسخهٔ همراه scikit-learn، کپی مجموعه‌دادهٔ WDBC متعلق به UCI است. فایل CSV همراه پروژه برای بازبینی و بازتولید آزمایش از همان نسخه ساخته شده است.', size=8.8, italic=True, color=(89,89,89))

# Core properties and save.
doc.core_properties.title = 'گزارش پروژه تشخیص سرطان سینه با یادگیری ماشین'
doc.core_properties.subject = 'مقایسه هفت الگوریتم روی مجموعه داده WDBC'
doc.core_properties.author = 'گزارش پروژه آموزشی'
doc.save(OUT)
print(OUT)
