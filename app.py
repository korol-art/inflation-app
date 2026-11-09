# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  «ГРОШІ ТА КРЕДИТ» · ІНФЛЯЦІЯ ТА ГРОШОВІ РЕФОРМИ                         ║
║  Інтерактивний практикум (Streamlit + Plotly + ReportLab)                ║
╚══════════════════════════════════════════════════════════════════════════╝

ЯК ЗАПУСТИТИ ЛОКАЛЬНО (Windows / macOS / Linux)
-----------------------------------------------
1. Встановіть Python 3.9+ та залежності:
       pip install streamlit plotly pandas numpy reportlab
2. Збережіть цей файл як app.py і запустіть:
       streamlit run app.py
3. Додаток відкриється у браузері за адресою http://localhost:8501
   З телефону в тій самій Wi-Fi мережі: http://<IP-комп'ютера>:8501

ЯК ЗАПУСТИТИ В GOOGLE COLAB
---------------------------
   Комірка 1:  !pip install -q streamlit plotly pandas numpy reportlab
   Комірка 2:  %%writefile app.py   ← і вставте весь код цього файлу
   Комірка 3:  !npm install -g localtunnel
   Комірка 4:  !streamlit run app.py &>/content/logs.txt &
               !curl ipv4.icanhazip.com        ← це «пароль» для localtunnel
               !npx localtunnel --port 8501    ← відкрийте отримане посилання

ХОСТИНГ ДЛЯ СТУДЕНТІВ (Streamlit Community Cloud, безкоштовно)
--------------------------------------------------------------
   Завантажте у репозиторій GitHub три файли:
     app.py
     requirements.txt   →  streamlit, plotly, pandas, numpy, reportlab
     packages.txt       →  fonts-dejavu-core   (шрифт з кирилицею для PDF)
   Студенти відкривають посилання на смартфонах — QR-код можна вивести на слайд.

ПРО PDF-ЕКСПОРТ
---------------
   Для української мови PDF потрібен TTF-шрифт з кирилицею. Додаток сам шукає
   DejaVu Sans / Arial у системі, а за відсутності — завантажує DejaVu Sans
   (потрібен інтернет під час першого експорту).

МОБІЛЬНА АДАПТАЦІЯ
------------------
   • CSS-медіазапити (≤768 px): компактні відступи, шрифти, стек колонок;
   • вкладки з горизонтальним прокручуванням, графіки без панелі інструментів
     і без «перехоплення» прокручування;
   • перемикач «Мобільний режим» у бічній панелі зменшує висоту графіків;
   • бокова панель за замовчуванням згорнута.

ДЖЕРЕЛА ДАНИХ: Держстат України, НБУ (bank.gov.ua). Дані 1990-х — орієнтовні,
для навчальної демонстрації; перед цитуванням у наукових роботах звіряйте
з офіційними публікаціями.
"""

import io
import math
import os
import tempfile
import urllib.request
from datetime import datetime
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    REPORTLAB_OK = True
except Exception:  # reportlab не встановлено
    REPORTLAB_OK = False

# ════════════════════════════════════════════════════════════════════════════
# 0. НАЛАШТУВАННЯ СТОРІНКИ ТА СТИЛІ (включно з мобільною адаптацією)
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Інфляція та грошові реформи",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 4rem; max-width: 1180px;}

/* Вкладки: горизонтальне прокручування замість переносу */
.stTabs [data-baseweb="tab-list"] {gap: 4px; overflow-x: auto; flex-wrap: nowrap;
    scrollbar-width: thin; -webkit-overflow-scrolling: touch;}
.stTabs [data-baseweb="tab"] {white-space: nowrap; padding: 8px 14px; border-radius: 8px 8px 0 0;}

/* Картка статусу інфляції */
.status-card {border-radius: 14px; padding: 18px 22px; margin: 6px 0 14px 0;}
.status-title {font-size: 1.45rem; font-weight: 700; line-height: 1.25;}
.status-rate {font-size: 2.3rem; font-weight: 800; color: #1b1b1b; margin: 2px 0 6px 0;}
.status-desc {font-size: 1rem; color: #222; line-height: 1.5;}

/* Блок-схеми причин */
.flow {display: flex; flex-wrap: wrap; align-items: stretch; gap: 8px; margin: 8px 0 14px 0;}
.flow-step {flex: 1 1 160px; border-radius: 12px; padding: 10px 12px; font-size: .93rem;
    line-height: 1.35; color: #1b1b1b;}
.flow-arrow {align-self: center; font-size: 1.5rem; color: #888;}
.s-demand {background: #e3f2fd; border: 1px solid #90caf9;}
.s-cost   {background: #fff3e0; border: 1px solid #ffcc80;}
.s-result {background: #ffebee; border: 1px solid #ef9a9a; font-weight: 600;}

/* Таймлайн */
.tl {border-left: 4px solid #2e7d32; margin: 8px 0 8px 8px; padding-left: 16px;}
.tl-item {margin-bottom: 14px; position: relative;}
.tl-item:before {content: ""; position: absolute; left: -24px; top: 5px; width: 12px; height: 12px;
    border-radius: 50%; background: #2e7d32; border: 2px solid #fff;}
.tl-date {font-weight: 700; color: #2e7d32;}

/* ───────── МОБІЛЬНА АДАПТАЦІЯ ───────── */
@media (max-width: 768px) {
  .block-container {padding: .6rem .7rem 3.5rem .7rem;}
  h1 {font-size: 1.55rem !important; line-height: 1.2 !important;}
  h2 {font-size: 1.25rem !important;}
  h3 {font-size: 1.1rem !important;}
  [data-testid="stMetricValue"] {font-size: 1.35rem !important;}
  [data-testid="stMetricLabel"] {font-size: .85rem !important;}
  .stTabs [data-baseweb="tab"] {padding: 6px 10px; font-size: .9rem;}
  .status-card {padding: 12px 14px;}
  .status-title {font-size: 1.15rem;}
  .status-rate {font-size: 1.8rem;}
  .status-desc {font-size: .92rem;}
  .flow {flex-direction: column;}
  .flow-arrow {transform: rotate(90deg);}
  .stButton > button, .stDownloadButton > button {min-height: 2.8rem; width: 100%;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}
NB = "\u00a0"  # нерозривний пробіл


# ════════════════════════════════════════════════════════════════════════════
# 1. ДОПОМІЖНІ ФУНКЦІЇ
# ════════════════════════════════════════════════════════════════════════════
def fmt(x, d=2):
    """Українське форматування числа: 12 345,67."""
    if x is None:
        return "—"
    try:
        if math.isnan(x) or math.isinf(x):
            return "—"
    except TypeError:
        return str(x)
    return f"{x:,.{d}f}".replace(",", NB).replace(".", ",")


def html(s):
    """Прибирає відступи, щоб Markdown не сприйняв HTML як блок коду."""
    return "".join(line.strip() for line in s.splitlines())


def stretch(fn, *args, **kwargs):
    """Розтягує віджет на всю ширину незалежно від версії Streamlit."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:
        return fn(*args, use_container_width=True, **kwargs)


def show_plot(fig, key=None):
    try:
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key=key)
    except Exception:
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG, key=key)


def style_fig(fig, height, title=None, legend_bottom=True):
    """Єдине оформлення графіків: компактні поля, горизонтальна легенда, без drag."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=15), x=0.01) if title else None,
        height=height,
        margin=dict(l=8, r=8, t=46 if title else 14, b=8),
        dragmode=False,
        hovermode="x unified",
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0, font=dict(size=11))
        if legend_bottom else dict(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(fixedrange=True, automargin=True, gridcolor="rgba(128,128,128,.18)")
    fig.update_yaxes(fixedrange=True, automargin=True, gridcolor="rgba(128,128,128,.18)")
    return fig


# ════════════════════════════════════════════════════════════════════════════
# 2. ДАНІ
# ════════════════════════════════════════════════════════════════════════════
# 2.1  Сучасна Україна (Держстат, НБУ)
UA_DATA = pd.DataFrame({
    "Рік": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
    "Інфляція, %": [9.8, 4.1, 5.0, 10.0, 26.6, 5.1, 12.0, 8.0, 10.0],
    "Облікова ставка, %": [18.0, 13.5, 6.0, 9.0, 25.0, 15.0, 13.5, 15.5, 16.5],
    "Дані": ["остаточні"] * 8 + ["попередні"],
})
UA_NOTE = ("Інфляція — грудень до грудня попереднього року (ІСЦ, Держстат). "
           "2026 р. — попередньо: вересень до вересня 2025 р.; прогноз НБУ на кінець 2026 р. — 12,5%. "
           "Облікова ставка — на кінець року; для 2026 р. — станом на 30.10.2026.")

# 2.2  Україна 1990-х: приріст цін за рік (грудень до грудня), орієнтовно
HIST = pd.DataFrame({
    "Рік": [1992, 1993, 1994, 1995, 1996, 1997],
    "Приріст цін, %": [2000.0, 10156.0, 401.0, 181.7, 39.7, 10.1],
})
HIST["Коефіцієнт за рік"] = 1 + HIST["Приріст цін, %"] / 100
HIST["Накопичений індекс (кін. 1991 = 1)"] = HIST["Коефіцієнт за рік"].cumprod()
KRB_PER_UAH = 100_000

# 2.3  Шкала видів інфляції
SCALE = pd.DataFrame({
    "Вид": ["Помірна (повзуча)", "Галопуюча", "Висока галопуюча", "Гіперінфляція"],
    "Темп за рік": ["до 10%", "10–50%", "50–200%", "понад 200%*"],
    "Ознаки": [
        "Гроші зберігають цінність, довгі кредити та контракти працюють",
        "Зростає недовіра до грошей, поширюється індексація та валютні розрахунки",
        "Втрата «якоря» цін, швидка заміна гривні валютою, тиск на зарплати",
        "Гроші втрачають функції засобу обігу і збереження вартості, бартер",
    ],
})
SCALE_FOOT = ("* У підручниках поріг гіперінфляції — понад 200% (в окремих джерелах — понад 1000%) на рік; "
              "за критерієм Ф. Кагана — понад 50% на місяць, що відповідає ≈12 875% на рік.")


def classify(rate):
    """Вид інфляції за річним темпом (приростом цін, %)."""
    if rate <= 10:
        return dict(name="Помірна (повзуча) інфляція", color="#2e7d32", bg="#e8f5e9", icon="🟢",
                    desc=("Ціни ростуть повільно — до 10% на рік. Гроші зберігають купівельну "
                          "спроможність, банки видають довгі кредити, а бізнес може планувати. "
                          "Ціль НБУ на середньострокову перспективу — 5%."))
    if rate <= 50:
        return dict(name="Галопуюча інфляція", color="#f9a825", bg="#fff8e1", icon="🟡",
                    desc=("Річний темп 10–50%. Населення й аграрії поспішають обміняти гроші на "
                          "товари та валюту, кредити дорожчають, договори індексують. Приклад: "
                          "2022 р. в Україні — 26,6%."))
    if rate <= 200:
        return dict(name="Висока галопуюча інфляція", color="#c62828", bg="#ffebee", icon="🔴",
                    desc=("Темп 50–200% на рік. Ціни мало пов'язані з витратами, заощадження "
                          "знецінюються за місяці, національну валюту витісняє іноземна. "
                          "Потрібні жорсткі стабілізаційні заходи. Приклад: Україна, 1995 р. — ≈182%."))
    return dict(name="Гіперінфляція", color="#7f0000", bg="#fdecea", icon="🔥",
                desc=("Понад 200% на рік (за Каганом — понад 50% на місяць). Гроші перестають "
                      "виконувати функції обігу та збереження вартості, зростає бартер, руйнується "
                      "кредит. Вихід — грошова реформа. Приклад: Україна, 1993 р. — понад 10 000%."))


def doubling_text(rate):
    if rate <= 0:
        return "ціни не зростають"
    months = 12 * math.log(2) / math.log(1 + rate / 100)
    if months >= 24:
        return f"≈ {fmt(months / 12, 1)} р."
    if months >= 1:
        return f"≈ {fmt(months, 1)} міс."
    return f"≈ {fmt(months * 30, 1)} дн."


# ════════════════════════════════════════════════════════════════════════════
# 3. ЕКСПОРТ У PDF
# ════════════════════════════════════════════════════════════════════════════
FONT_PAIRS = [  # (звичайний, жирний)
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ("C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"),
    ("C:\\Windows\\Fonts\\calibri.ttf", "C:\\Windows\\Fonts\\calibrib.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]
FONT_URLS = {
    "DejaVuSans.ttf": "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf": "https://raw.githubusercontent.com/matplotlib/matplotlib/main/lib/matplotlib/mpl-data/fonts/ttf/DejaVuSans-Bold.ttf",
}


@st.cache_resource(show_spinner=False)
def find_fonts():
    """Повертає шляхи (regular, bold) до TTF-шрифту з кирилицею."""
    for reg, bold in FONT_PAIRS:
        if os.path.exists(reg) and os.path.exists(bold):
            return reg, bold
    try:  # шрифти, що йдуть разом з matplotlib
        import matplotlib
        d = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
        reg, bold = os.path.join(d, "DejaVuSans.ttf"), os.path.join(d, "DejaVuSans-Bold.ttf")
        if os.path.exists(reg) and os.path.exists(bold):
            return reg, bold
    except Exception:
        pass
    cache_dir = os.path.join(tempfile.gettempdir(), "uk_pdf_fonts")  # завантаження
    os.makedirs(cache_dir, exist_ok=True)
    paths = []
    for fname, url in FONT_URLS.items():
        target = os.path.join(cache_dir, fname)
        if not os.path.exists(target):
            urllib.request.urlretrieve(url, target)
        paths.append(target)
    return paths[0], paths[1]


def register_fonts():
    reg, bold = find_fonts()
    pdfmetrics.registerFont(TTFont("UA", reg))
    pdfmetrics.registerFont(TTFont("UA-B", bold))
    pdfmetrics.registerFontFamily("UA", normal="UA", bold="UA-B", italic="UA", boldItalic="UA-B")
    return "UA", "UA-B"


def build_pdf(rep, sections, author, group, conclusions):
    """Формує PDF-звіт за результатами, що зібрані у словнику rep."""
    F, FB = register_fonts()
    green, light = colors.HexColor("#1b5e20"), colors.HexColor("#e8f5e9")

    st_body = ParagraphStyle("b", fontName=F, fontSize=9.5, leading=13.5, alignment=TA_LEFT, spaceAfter=4)
    st_small = ParagraphStyle("s", parent=st_body, fontSize=8, leading=10.5, textColor=colors.HexColor("#555555"))
    st_h1 = ParagraphStyle("h1", fontName=FB, fontSize=17, leading=21, textColor=green, spaceAfter=4)
    st_h2 = ParagraphStyle("h2", fontName=FB, fontSize=12.5, leading=16, textColor=green, spaceBefore=12, spaceAfter=5)
    st_cell = ParagraphStyle("c", fontName=F, fontSize=8.5, leading=11)
    st_cell_b = ParagraphStyle("cb", parent=st_cell, fontName=FB)
    st_head = ParagraphStyle("hd", parent=st_cell, fontName=FB, textColor=colors.white)

    def P(text, style=st_body, raw=False):
        t = text if raw else escape(str(text))
        return Paragraph(t.replace("\n", "<br/>"), style)

    def tbl(rows, widths, header=True, bold_first_col=False):
        data = []
        for r_i, row in enumerate(rows):
            cells = []
            for c_i, v in enumerate(row):
                if header and r_i == 0:
                    cells.append(Paragraph(escape(str(v)), st_head))
                elif bold_first_col and c_i == 0:
                    cells.append(Paragraph(escape(str(v)), st_cell_b))
                else:
                    cells.append(Paragraph(escape(str(v)), st_cell))
            data.append(cells)
        t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
        style = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b0bec5")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f9f5")]),
        ]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), green))
        t.setStyle(TableStyle(style))
        return t

    def bullets(items):
        return [P("•  " + s, st_body) for s in items]

    def chart(years, infl, rate):
        w, h = 174 * mm, 62 * mm
        d = Drawing(w, h)
        bc = VerticalBarChart()
        bc.x, bc.y, bc.width, bc.height = 30, 24, w - 40, h - 44
        bc.data = [list(infl), list(rate)]
        bc.categoryAxis.categoryNames = [str(y) for y in years]
        bc.categoryAxis.labels.fontName, bc.categoryAxis.labels.fontSize = F, 8
        bc.valueAxis.labels.fontName, bc.valueAxis.labels.fontSize = F, 8
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = math.ceil(max(max(infl), max(rate)) * 1.2 / 5) * 5
        bc.valueAxis.valueStep = 5
        bc.bars[0].fillColor = colors.HexColor("#2e7d32")
        bc.bars[1].fillColor = colors.HexColor("#ef6c00")
        bc.barLabelFormat = lambda v: fmt(v, 1)
        bc.barLabels.fontName, bc.barLabels.fontSize, bc.barLabels.nudge = F, 6.5, 6
        bc.groupSpacing, bc.barSpacing = 8, 1
        d.add(bc)
        d.add(Rect(30, h - 14, 8, 8, fillColor=colors.HexColor("#2e7d32"), strokeColor=None))
        d.add(String(42, h - 13, "Інфляція, % (грудень до грудня)", fontName=F, fontSize=8))
        d.add(Rect(215, h - 14, 8, 8, fillColor=colors.HexColor("#ef6c00"), strokeColor=None))
        d.add(String(227, h - 13, "Облікова ставка НБУ, % (кінець року)", fontName=F, fontSize=8))
        return d

    story = [
        P("Інфляція та грошові реформи", st_h1),
        P("Дисципліна «Гроші та кредит» · звіт за результатами інтерактивного практикуму", st_small),
        Spacer(1, 4),
        tbl([["Виконавець", author.strip() or "—"],
             ["Група / курс", group.strip() or "—"],
             ["Дата формування", datetime.now().strftime("%d.%m.%Y %H:%M")],
             ["Розділи звіту", ", ".join(sections)]], [40, 134], header=False, bold_first_col=True),
    ]

    # ── Розділ 1
    if "1. Види інфляції" in sections:
        r = rep["s1"]
        story += [P("1. Суть та види інфляції", st_h2),
                  P(f"Задана річна інфляція: {fmt(r['rate'], 1)}%. Класифікація: {r['name']}.", st_body),
                  tbl([["Показник", "Значення"],
                       ["Еквівалентний місячний темп", f"{fmt(r['monthly'], 2)}%"],
                       ["Ціни за рік зростуть у", f"{fmt(r['factor'], 2)} раза"],
                       ["Купівельна спроможність 1 000 грн через рік", f"{fmt(r['power'], 2)} грн"],
                       ["Час подвоєння цін", r["double"]]], [100, 74]),
                  Spacer(1, 4), P(r["desc"], st_body), Spacer(1, 3),
                  tbl([["Вид", "Темп за рік", "Ознаки"]] + SCALE.values.tolist(), [38, 28, 108]),
                  P(SCALE_FOOT, st_small)]

    # ── Розділ 2
    if "2. Причини та механізм" in sections:
        r = rep["s2"]
        story += [P("2. Причини та механізм: попит чи витрати", st_h2),
                  P(f"Параметри сценарію: шок попиту {r['dem']:+.0f}; шок витрат {r['cost']:+.0f}; "
                    f"підвищення облікової ставки {r['di']:.1f} в.п. (модель AD–AS, базовий рівень цін = 100).", st_body),
                  tbl([["Показник", "Базовий стан", "Після шоків (з урахуванням ставки)", "Без підвищення ставки"],
                       ["Рівень цін (база = 100)", fmt(r["P0"], 1), fmt(r["P1"], 1), fmt(r["Pnh"], 1)],
                       ["Випуск (ВВП, ум. од.)", fmt(r["Y0"], 1), fmt(r["Y1"], 1), fmt(r["Ynh"], 1)],
                       ["Розрив випуску, % від потенційного", "0,0", fmt(r["gap1"], 1), fmt(r["gapnh"], 1)]],
                      [54, 28, 50, 42]),
                  Spacer(1, 4)] + bullets(r["notes"])

    # ── Розділ 3
    if "3. Реформи 90-х" in sections:
        r = rep["s3"]
        story += [P("3. Гіперінфляція 1990-х і грошова реформа 1996 р.", st_h2),
                  P(f"Режим калькулятора: {r['mode']}.", st_body),
                  tbl([["Показник", "Значення"]] + r["rows"], [100, 74]), Spacer(1, 4),
                  tbl([["Рік", "Приріст цін, %", "Коефіцієнт за рік", "Накопичений індекс (кін. 1991 = 1)"]] +
                      [[str(int(a)), fmt(b, 1), fmt(c, 2), fmt(d, 0)] for a, b, c, d in HIST.values],
                      [20, 40, 45, 69]),
                  P("Грошова реформа: 2–16 вересня 1996 р. карбованці обмінювали на гривні за курсом "
                    "100 000 : 1 (1 грн = 100 коп.). Дані 1990-х — орієнтовні (Держкомстат/НБУ).", st_small)]

    # ── Розділ 4
    if "4. Індекси цін" in sections:
        r = rep["s4"]
        story += [P("4. Практикум: індекси Ласпейреса, Пааше, Фішера", st_h2)]
        if r["ok"]:
            d = r["df"]
            rows = [["Товар", "Од.", "P0", "Q0", "P1", "Q1"]]
            for _, x in d.iterrows():
                rows.append([x["Товар"], x["Одиниця"], fmt(x["P0"]), fmt(x["Q0"], 0), fmt(x["P1"]), fmt(x["Q1"], 0)])
            story += [tbl(rows, [50, 16, 28, 26, 28, 26]), Spacer(1, 4),
                      tbl([["Індекс", "Формула", "Значення", "Інфляція, %"],
                           ["Ласпейреса, IL", "ΣP1Q0 / ΣP0Q0", fmt(r["IL"], 4), fmt((r["IL"] - 1) * 100, 2)],
                           ["Пааше, IP", "ΣP1Q1 / ΣP0Q1", fmt(r["IP"], 4), fmt((r["IP"] - 1) * 100, 2)],
                           ["Фішера, IF", "√(IL · IP)", fmt(r["IF"], 4), fmt((r["IF"] - 1) * 100, 2)]],
                          [40, 50, 40, 44]),
                      Spacer(1, 4)] + bullets(r["notes"])
        else:
            story.append(P("Дані введено некоректно (порожні клітинки або нульова база) — розрахунок не виконано.", st_body))

    # ── Розділ 5
    if "5. Динаміка в Україні" in sections:
        r = rep["s5"]
        d = r["df"]
        rows = [["Рік", "Інфляція, %", "Облікова ставка, %", "Реальна ставка, в.п.", "Дані"]]
        for _, x in d.iterrows():
            rows.append([str(int(x["Рік"])), fmt(x["Інфляція, %"], 1), fmt(x["Облікова ставка, %"], 1),
                         fmt(x["Облікова ставка, %"] - x["Інфляція, %"], 1), x["Дані"]])
        story += [P("5. Динаміка інфляції в Україні", st_h2),
                  chart(d["Рік"].tolist(), d["Інфляція, %"].tolist(), d["Облікова ставка, %"].tolist()),
                  Spacer(1, 4), tbl(rows, [20, 34, 44, 44, 32])] + [Spacer(1, 4)] + bullets(r["notes"]) + \
                 [P(UA_NOTE, st_small)]

    if conclusions.strip():
        story += [P("Висновки виконавця", st_h2), P(conclusions)]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(F, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(18 * mm, 9 * mm, "Гроші та кредит · Інфляція та грошові реформи")
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Сторінка {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=18 * mm,
                            title="Інфляція та грошові реформи", author=author or "Студент")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# 4. СТАН СЕСІЇ ТА БОКОВА ПАНЕЛЬ
# ════════════════════════════════════════════════════════════════════════════
ss = st.session_state
ss.setdefault("infl_slider", 8)
ss.setdefault("use_big", False)
ss.setdefault("infl_big", 10156.0)
ss.setdefault("dem", 20)
ss.setdefault("cost", 0)
ss.setdefault("di", 0.0)
ss.setdefault("idx_ver", 0)
ss.setdefault("pdf_bytes", None)

report = {}  # сюди кожна вкладка складає результати для PDF

with st.sidebar:
    st.header("⚙️ Налаштування")
    mobile = st.toggle("📱 Мобільний режим", value=False,
                       help="Зменшує висоту графіків для екранів смартфонів.")
    st.caption("Додаток автоматично адаптується до ширини екрана; перемикач лише робить графіки нижчими.")
    st.divider()
    st.markdown("**Джерела даних**\n\n- Держстат України\n- НБУ (bank.gov.ua)\n\n"
                "Дані 1990-х років — орієнтовні, для навчальної демонстрації.")
H = 300 if mobile else 440

st.title("💹 Інфляція та грошові реформи")
st.caption("Дисципліна «Гроші та кредит» · інтерактивний практикум для лекцій і практичних занять")

tabs = st.tabs(["1 · Суть і види", "2 · Причини", "3 · Реформи 90-х", "4 · Індекси цін", "5 · Динаміка"])

# ════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА 1. СУТЬ ТА ВИДИ ІНФЛЯЦІЇ
# ════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.header("1. Суть та види інфляції")
    st.markdown("**Інфляція** — тривале загальне підвищення рівня цін, що супроводжується "
                "знеціненням грошей і зниженням їхньої купівельної спроможності.")
    st.latex(r"\pi = \frac{P_t - P_{t-1}}{P_{t-1}} \cdot 100\%")

    def set_example(v):
        if v <= 1000:
            ss["use_big"] = False
            ss["infl_slider"] = int(v)
        else:
            ss["use_big"] = True
            ss["infl_big"] = float(v)

    st.slider("Річний темп інфляції, %", 0, 1000, key="infl_slider",
              help="Для значень понад 1000% увімкніть перемикач нижче.")
    st.checkbox("Ввести значення понад 1000%", key="use_big")
    if ss["use_big"]:
        st.number_input("Темп інфляції, % на рік", min_value=1000.0, max_value=1e9, step=1000.0, key="infl_big")
    rate = float(ss["infl_big"]) if ss["use_big"] else float(ss["infl_slider"])

    st.caption("Швидкий вибір історичних прикладів:")
    ex_cols = st.columns(4)
    examples = [("2020 р. ≈5%", 5), ("2022 р. ≈27%", 27), ("1995 р. ≈182%", 182), ("1993 р. ≈10 156%", 10156)]
    for col, (lbl, val) in zip(ex_cols, examples):
        with col:
            stretch(st.button, lbl, key=f"ex_{val}", on_click=set_example, args=(val,))

    cls = classify(rate)
    rate_txt = fmt(rate, 0) if rate >= 1000 else fmt(rate, 1)
    st.markdown(html(f"""
        <div class="status-card" style="background:{cls['bg']}; border-left:10px solid {cls['color']};">
          <div class="status-title" style="color:{cls['color']};">{cls['icon']} {cls['name']}</div>
          <div class="status-rate">{rate_txt}% на рік</div>
          <div class="status-desc">{cls['desc']}</div>
        </div>"""), unsafe_allow_html=True)

    factor = 1 + rate / 100
    monthly = (factor ** (1 / 12) - 1) * 100
    power = 1000 / factor
    dbl = doubling_text(rate)
    if rate >= 12875:
        st.info("Виконується й критерій Кагана: понад 50% приросту цін за місяць.")

    m1, m2 = st.columns(2)
    m1.metric("Еквівалентний місячний темп", f"{fmt(monthly, 2)}%")
    m2.metric("Ціни за рік зростуть у", f"{fmt(factor, 2)} раза")
    m3, m4 = st.columns(2)
    m3.metric("1 000 грн через рік «коштуватимуть»", f"{fmt(power, 2)} грн", delta=f"{fmt(power - 1000, 2)} грн",
              delta_color="inverse")
    m4.metric("Ціни подвояться за", dbl)

    t = np.arange(0, 6)
    fig = go.Figure(go.Scatter(x=t, y=1000 / factor ** t, mode="lines+markers", line=dict(color=cls["color"], width=3),
                               marker=dict(size=8), name="Реальна вартість 1 000 грн",
                               hovertemplate="Через %{x} р.: %{y:,.2f} грн<extra></extra>"))
    style_fig(fig, H, "Знецінення 1 000 грн за 5 років (у цінах сьогодні)", legend_bottom=False)
    fig.update_xaxes(title="Років", dtick=1)
    fig.update_yaxes(title="грн", type="log" if rate > 100 else "linear")
    show_plot(fig, key="fig_depr")

    with st.expander("📋 Класична шкала видів інфляції", expanded=False):
        st.table(SCALE)
        st.caption(SCALE_FOOT)

    report["s1"] = dict(rate=rate, name=cls["name"], desc=cls["desc"], monthly=monthly, factor=factor,
                        power=power, double=dbl)

# ════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА 2. ПРИЧИНИ ТА МЕХАНІЗМ
# ════════════════════════════════════════════════════════════════════════════
BASE_A, BASE_C, SLOPE_D, SLOPE_S = 140.0, 60.0, 0.5, 0.5
Y_POT, K_RATE = 80.0, 3.0   # потенційний випуск; зсув AD на 1 в.п. ставки


def equilibrium(a, c):
    y = (a - c) / (SLOPE_D + SLOPE_S)
    return y, c + SLOPE_S * y


def set_preset(dem, cost, di):
    ss["dem"], ss["cost"], ss["di"] = dem, cost, di


with tabs[1]:
    st.header("2. Причини та механізм інфляції")
    kind = st.radio("Тип інфляції", ["📈 Інфляція попиту (demand-pull)", "⛽ Інфляція витрат (cost-push)"],
                    horizontal=True, label_visibility="collapsed")
    if kind.startswith("📈"):
        steps = ["💵 Зростання доходів, кредитування, бюджетних видатків, грошової маси",
                 "🛒 Зростає сукупний попит (крива AD зсувається праворуч)",
                 "⚖️ Попит перевищує пропозицію за майже повного завантаження ресурсів",
                 "📈 Ціни ростуть, ВВП — вище потенційного"]
        cls_ = ["s-demand", "s-demand", "s-demand", "s-result"]
        ex = ("**Агро-приклад.** Високі ціни на зерно та бум кредитування ферм підвищують попит на техніку, "
              "землю та послуги — вони дорожчають швидше за можливості їх швидко наростити.")
    else:
        steps = ["⛽ Подорожчання палива, добрив, насіння, електроенергії, праці, курсу валюти",
                 "🚜 Зростає собівартість; виробники скорочують пропозицію (крива AS зсувається вгору-ліворуч)",
                 "⚖️ Менше товарів за вищою ціною",
                 "📈 Ціни ростуть, а випуск і зайнятість падають — стагфляція"]
        cls_ = ["s-cost", "s-cost", "s-cost", "s-result"]
        ex = ("**Агро-приклад.** Стрибок цін на дизельне пальне та азотні добрива збільшує собівартість "
              "вирощування зернових; агрофірма зменшує площі або внесення добрив — пропозиція скорочується, "
              "ціни на ринку зростають.")
    flow = ""
    for i, (s, c) in enumerate(zip(steps, cls_)):
        flow += f'<div class="flow-step {c}">{s}</div>'
        if i < len(steps) - 1:
            flow += '<div class="flow-arrow">➜</div>'
    st.markdown(html(f'<div class="flow">{flow}</div>'), unsafe_allow_html=True)
    st.markdown(ex)

    st.subheader("🔬 Модель AD–AS: що може НБУ?")
    st.caption("Оберіть готовий сценарій або задайте шоки власноруч. Базовий стан: рівень цін = 100, "
               "випуск = потенційному (80).")
    pc = st.columns(3)
    with pc[0]:
        stretch(st.button, "📈 Бум попиту", key="pre1", on_click=set_preset, args=(25, 0, 0.0))
    with pc[1]:
        stretch(st.button, "⛽ Шок палива", key="pre2", on_click=set_preset, args=(0, 25, 0.0))
    with pc[2]:
        stretch(st.button, "⛽ Шок + ставка", key="pre3", on_click=set_preset, args=(0, 25, 6.0))

    sc = st.columns(3)
    dem = sc[0].slider("Шок попиту (зсув AD)", -30, 40, key="dem")
    cost = sc[1].slider("Шок витрат (зсув AS)", -10, 40, key="cost")
    di = sc[2].slider("Підвищення ставки НБУ, в.п.", 0.0, 10.0, step=0.5, key="di")

    Y0, P0 = equilibrium(BASE_A, BASE_C)
    A1, C1 = BASE_A + dem - K_RATE * di, BASE_C + cost
    Y1, P1 = equilibrium(A1, C1)
    Ynh, Pnh = equilibrium(BASE_A + dem, C1)
    gap1, gapnh = (Y1 - Y_POT) / Y_POT * 100, (Ynh - Y_POT) / Y_POT * 100

    mm1, mm2 = st.columns(2)
    mm1.metric("Зміна рівня цін", f"{fmt((P1 / P0 - 1) * 100, 1)}%", delta=f"{fmt(P1 - Pnh, 1)} п. від ставки",
               delta_color="off")
    mm2.metric("Розрив випуску", f"{fmt(gap1, 1)}%", delta=f"{fmt(gap1 - gapnh, 1)} п. від ставки", delta_color="off")

    ys = np.linspace(0, 160, 81)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ys, y=BASE_A - SLOPE_D * ys, name="AD (база)", line=dict(color="#90a4ae", dash="dash")))
    fig.add_trace(go.Scatter(x=ys, y=BASE_C + SLOPE_S * ys, name="AS (база)", line=dict(color="#bcaaa4", dash="dash")))
    fig.add_trace(go.Scatter(x=ys, y=A1 - SLOPE_D * ys, name="AD (новий)", line=dict(color="#1565c0", width=3)))
    fig.add_trace(go.Scatter(x=ys, y=C1 + SLOPE_S * ys, name="AS (новий)", line=dict(color="#ef6c00", width=3)))
    fig.add_vline(x=Y_POT, line=dict(color="#6a1b9a", dash="dot"),
                  annotation_text="Y потенц.", annotation_position="top")
    fig.add_trace(go.Scatter(x=[Y0], y=[P0], mode="markers+text", text=["E₀"], textposition="top right",
                             marker=dict(size=11, color="#455a64"), name="Базова рівновага"))
    fig.add_trace(go.Scatter(x=[Y1], y=[P1], mode="markers+text", text=["E₁"], textposition="top right",
                             marker=dict(size=13, color="#c62828"), name="Нова рівновага"))
    style_fig(fig, H + 20, "Рівновага: рівень цін (P) і випуск (Y)")
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(title="Випуск, Y", range=[0, 160])
    fig.update_yaxes(title="Рівень цін, P", range=[0, 220])
    show_plot(fig, key="fig_adas")

    # Автоматична діагностика
    notes = []
    if dem > 0 and cost <= 0:
        notes.append("Це інфляція попиту: ціни й випуск зростають одночасно, випуск перевищує потенційний рівень.")
    elif cost > 0 and dem <= 0:
        notes.append("Це інфляція витрат (шок пропозиції): ціни зростають, а випуск падає нижче потенційного — стагфляція.")
    elif cost > 0 and dem > 0:
        notes.append("Змішаний випадок: діють і тиск попиту, і подорожчання витрат.")
    else:
        notes.append("Інфляційних шоків немає або вони від'ємні — ціни не зростають.")
    if di > 0:
        if gap1 < -1:
            notes.append(f"Підвищення ставки знизило ціни на {fmt(Pnh - P1, 1)} п., але поглибило спад: випуск на "
                         f"{fmt(abs(gap1), 1)}% нижчий за потенційний. За шоку витрат ставка «лікує» наслідок, а не причину.")
        elif abs(gap1) <= 1:
            notes.append("Підвищення ставки охолодило попит і повернуло економіку до потенційного випуску — "
                         "саме так працює монетарна політика проти інфляції попиту.")
        else:
            notes.append(f"Ставка зменшила інфляційний тиск на {fmt(Pnh - P1, 1)} п., але розрив попиту ще "
                         f"залишається ({fmt(gap1, 1)}%) — потрібне додаткове посилення.")
    elif dem > 0 or cost > 0:
        notes.append("Спробуйте підвищити ставку НБУ повзунком і порівняйте результат у двох сценаріях.")
    for n in notes:
        st.info(n)

    with st.expander("📖 Чому ставка НБУ ефективна проти інфляції попиту, але не проти шоків пропозиції?", expanded=True):
        st.markdown("""
**Канал дії облікової ставки.** Вища ставка → дорожчають кредити, привабливішими стають депозити →
скорочуються споживання та інвестиції → зменшується сукупний попит (AD зсувається **ліворуч**).
""")
        st.latex(r"r \approx i - \pi^{e}")
        st.markdown("""
**Інфляція попиту.** Причина інфляції — надлишок попиту. Ставка усуває саме причину: AD повертається до
рівноваги, ціни перестають зростати, а випуск повертається до потенційного.

**Інфляція витрат.** Причина — підвищення собівартості (пальне, добрива, курс, логістика), яке не залежить від
внутрішнього попиту. Вища ставка:
- не здешевлює нафту, газ чи добрива на світових ринках;
- послаблює попит і тому *знижує* ціни, але **ціною падіння випуску й зайнятості**;
- підвищує вартість кредитів аграріїв — витрати зростають ще більше (оборотні кошти, лізинг техніки).

**Висновок.** Проти шоків пропозиції найкраще працюють не лише монетарні, а й немонетарні заходи:
диверсифікація імпорту, логістика, страхування, підтримка виробників. Центробанк здебільшого стримує
**вторинні ефекти** — щоб разове подорожчання не закріпилося в очікуваннях.
""")
        st.info("**Кейс 2026 р.** За повідомленнями НБУ, у липні, вересні та жовтні 2026 р. облікову ставку "
                "підвищували (до 16,5% від 30.10.2026) на тлі зростання цін на енергоносії та наслідків "
                "обстрілів; прогноз інфляції на кінець року — 12,5%. Обговоріть зі студентами: який тут "
                "переважає тиск — попиту чи витрат? Актуальні дані — на bank.gov.ua.")

    report["s2"] = dict(dem=dem, cost=cost, di=di, P0=P0, Y0=Y0, P1=P1, Y1=Y1, Pnh=Pnh, Ynh=Ynh,
                        gap1=gap1, gapnh=gapnh, notes=notes)

# ════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА 3. ІСТОРІЯ ТА РЕФОРМИ
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.header("3. Гіперінфляція 90-х і грошова реформа 1996 р.")
    mode = st.radio("Режим калькулятора", ["💱 Конвертація в гривні", "📉 Знецінення та зарплата"], horizontal=True)
    years = HIST["Рік"].tolist()
    cum = dict(zip(HIST["Рік"], HIST["Накопичений індекс (кін. 1991 = 1)"]))
    cum[1991] = 1.0
    rows3 = []

    if mode.startswith("💱"):
        amount = st.number_input("Сума, карбованці (купони)", min_value=0.0, value=1_000_000.0, step=100_000.0, format="%.0f")
        uah = amount / KRB_PER_UAH
        c1, c2 = st.columns(2)
        c1.metric("Еквівалент у гривнях", f"{fmt(uah, 2)} грн")
        c2.metric("У копійках", f"{fmt(uah * 100, 0)} коп.")
        st.caption("Обмін 2–16 вересня 1996 р.: 100 000 карбованців = 1 гривня (1 грн = 100 коп.). "
                   "Найбільша банкнота — 1 000 000 карб. — дорівнювала 10 грн.")
        rows3 = [["Сума, карбованців", fmt(amount, 0)], ["Еквівалент, грн (1 : 100 000)", fmt(uah, 2)]]
        y_from, y_to = 1992, 1996
    else:
        y_from, y_to = st.select_slider("Період (роки)", options=years, value=(1993, 1995))
        s1, s2 = st.columns(2)
        sal = s1.number_input("Зарплата на початку періоду, карб./міс.", min_value=0.0, value=100_000.0,
                              step=10_000.0, format="%.0f")
        nom = s2.number_input("Номінальна зарплата зросла в ... разів", min_value=0.0, value=800.0, step=10.0)
        price_x = cum[y_to] / cum[y_from - 1]
        real_x = nom / price_x
        sal_end = sal * nom
        e1, e2 = st.columns(2)
        e1.metric("Ціни за період зросли у", f"{fmt(price_x, 1)} раза")
        e2.metric("Зарплата наприкінці періоду", f"{fmt(sal_end, 0)} карб.")
        e3, e4 = st.columns(2)
        e3.metric("Реальна зарплата (до початку = 100%)", f"{fmt(real_x * 100, 1)}%",
                  delta=f"{fmt((real_x - 1) * 100, 1)}%", delta_color="normal")
        e4.metric("Зарплата в гривнях (1 : 100 000)", f"{fmt(sal_end / KRB_PER_UAH, 2)} грн")
        if real_x < 1:
            st.warning("Зарплата зросла повільніше за ціни — купівельна спроможність упала.")
        else:
            st.success("Зарплата випередила зростання цін — купівельна спроможність зросла.")
        rows3 = [["Період", f"{y_from}–{y_to}"], ["Ціни зросли у (разів)", fmt(price_x, 1)],
                 ["Зарплата на початку, карб.", fmt(sal, 0)], ["Номінальне зростання зарплати (разів)", fmt(nom, 1)],
                 ["Зарплата в кінці, карб.", fmt(sal_end, 0)], ["Реальна зарплата, % від початкової", fmt(real_x * 100, 1)]]

    xs = [1991] + years
    ys_ = [1.0] + [cum[y] for y in years]
    fig = go.Figure(go.Scatter(x=[str(x) for x in xs], y=ys_, mode="lines+markers", line=dict(color="#c62828", width=3),
                               name="Накопичений індекс цін",
                               hovertemplate="Кінець %{x}: ×%{y:,.0f}<extra></extra>"))
    fig.add_vrect(x0=str(y_from - 1) if mode.startswith("📉") else "1991", x1=str(y_to),
                  fillcolor="rgba(46,125,50,.12)", line_width=0)
    style_fig(fig, H, "Накопичений рівень цін (кінець 1991 р. = 1), логарифмічна шкала", legend_bottom=False)
    fig.update_yaxes(type="log", title="разів")
    show_plot(fig, key="fig_hist")

    st.subheader("🕰️ Хронологія")
    st.markdown(html("""
    <div class="tl">
      <div class="tl-item"><span class="tl-date">24 серпня 1991</span><br>Проголошення незалежності. Грошова одиниця — радянський карбованець (рубльова зона).</div>
      <div class="tl-item"><span class="tl-date">Січень 1992</span><br>Лібералізація цін; введено «купони багаторазового використання» поряд із карбованцем. Інфляція за рік — понад 2000%.</div>
      <div class="tl-item"><span class="tl-date">12 листопада 1992</span><br>Купон стає єдиним законним платіжним засобом — вихід із рубльової зони.</div>
      <div class="tl-item"><span class="tl-date">1993</span><br>Гіперінфляція: ціни зросли більш ніж у 100 разів (≈10 000% за рік).</div>
      <div class="tl-item"><span class="tl-date">1994–1995</span><br>Програма макростабілізації; темпи падають до ≈400% і ≈180%. В обігу — банкноти до 1 000 000 карб.</div>
      <div class="tl-item"><span class="tl-date">2–16 вересня 1996</span><br><b>Грошова реформа</b> (Указ Президента №762/96): обмін 100 000 карб. на 1 гривню, введення копійки; курс — 1,76 грн/USD.</div>
      <div class="tl-item"><span class="tl-date">1996–1997</span><br>Інфляція знижується до 39,7% і 10,1%.</div>
    </div>"""), unsafe_allow_html=True)

    disp = HIST.copy()
    disp["Рік"] = disp["Рік"].astype(str)
    disp["Накопичений індекс (кін. 1991 = 1)"] = disp["Накопичений індекс (кін. 1991 = 1)"].round(0)
    with st.expander("📊 Таблиця щорічних темпів (орієнтовно)"):
        stretch(st.dataframe, disp, hide_index=True)
        st.caption("Приріст цін за грудень до грудня; значення округлені, у джерелах трапляються розбіжності.")

    report["s3"] = dict(mode=mode.split(" ", 1)[1], rows=rows3)

# ════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА 4. ІНДЕКСИ ЦІН
# ════════════════════════════════════════════════════════════════════════════
DEFAULT_IDX = pd.DataFrame({
    "Товар": ["Пшениця", "Дизельне пальне", "Аміачна селітра"],
    "Одиниця": ["т", "л", "т"],
    "P0": [6500.0, 41.0, 14000.0], "Q0": [120.0, 5000.0, 20.0],
    "P1": [8200.0, 53.0, 21000.0], "Q1": [110.0, 4200.0, 15.0],
})


def random_idx():
    rng = np.random.default_rng()
    p0 = np.array([rng.uniform(5500, 7500), rng.uniform(38, 45), rng.uniform(12000, 17000)])
    q0 = np.array([rng.integers(80, 150), rng.integers(3000, 8000), rng.integers(10, 30)], dtype=float)
    p1 = p0 * rng.uniform(1.05, 1.55, 3)
    q1 = np.round(q0 * rng.uniform(0.75, 1.10, 3))
    return pd.DataFrame({"Товар": DEFAULT_IDX["Товар"], "Одиниця": DEFAULT_IDX["Одиниця"],
                         "P0": p0.round(2), "Q0": q0, "P1": p1.round(2), "Q1": q1})


def reset_idx():
    ss["idx_df"], ss["idx_ver"] = DEFAULT_IDX.copy(), ss["idx_ver"] + 1


def gen_idx():
    ss["idx_df"], ss["idx_ver"] = random_idx(), ss["idx_ver"] + 1


ss.setdefault("idx_df", DEFAULT_IDX.copy())

with tabs[3]:
    st.header("4. Практикум: індекси Ласпейреса, Пааше, Фішера")
    st.caption("Змініть значення в таблиці (двічі торкніться клітинки) або згенеруйте нові дані.")
    bcol = st.columns(2)
    with bcol[0]:
        stretch(st.button, "🔄 Приклад за замовчуванням", key="b_reset", on_click=reset_idx)
    with bcol[1]:
        stretch(st.button, "🎲 Згенерувати дані", key="b_gen", on_click=gen_idx)

    num = lambda lbl: st.column_config.NumberColumn(lbl, min_value=0.0, format="%.2f")
    edited = stretch(
        st.data_editor, ss["idx_df"], key=f"idx_editor_{ss['idx_ver']}", hide_index=True, num_rows="fixed",
        column_config={"Товар": st.column_config.TextColumn("Товар", required=True),
                       "Одиниця": st.column_config.TextColumn("Од."),
                       "P0": num("P₀ (база)"), "Q0": num("Q₀ (база)"),
                       "P1": num("P₁ (звіт)"), "Q1": num("Q₁ (звіт)")})
    d = edited.copy()
    numcols = ["P0", "Q0", "P1", "Q1"]
    ok = not d[numcols].isna().any().any()
    r4 = dict(ok=False)
    if ok:
        d[numcols] = d[numcols].astype(float)
        sum_l0, sum_l1 = (d.P0 * d.Q0).sum(), (d.P1 * d.Q0).sum()
        sum_p0, sum_p1 = (d.P0 * d.Q1).sum(), (d.P1 * d.Q1).sum()
        ok = sum_l0 > 0 and sum_p0 > 0
    if not ok:
        st.warning("Заповніть усі клітинки невід'ємними числами; базова вартість кошика має бути більшою за нуль.")
    else:
        IL, IP = sum_l1 / sum_l0, sum_p1 / sum_p0
        IF = math.sqrt(IL * IP)
        st.latex(r"I_L=\frac{\sum P_1 Q_0}{\sum P_0 Q_0},\quad I_P=\frac{\sum P_1 Q_1}{\sum P_0 Q_1},\quad I_F=\sqrt{I_L\cdot I_P}")
        k = st.columns(3)
        for col, (lbl, v) in zip(k, [("Ласпейреса, I_L", IL), ("Пааше, I_P", IP), ("Фішера, I_F", IF)]):
            col.metric(lbl, fmt(v, 4), delta=f"{fmt((v - 1) * 100, 2)}%", delta_color="inverse")

        fig = go.Figure(go.Bar(x=["Ласпейрес", "Пааше", "Фішер"], y=[(IL - 1) * 100, (IP - 1) * 100, (IF - 1) * 100],
                               marker_color=["#1565c0", "#ef6c00", "#2e7d32"],
                               text=[f"{fmt((v - 1) * 100, 1)}%" for v in (IL, IP, IF)], textposition="outside",
                               hovertemplate="%{x}: %{y:.2f}%<extra></extra>"))
        style_fig(fig, H - 40, "Приріст цін за методиками, %", legend_bottom=False)
        fig.update_yaxes(title="%")
        show_plot(fig, key="fig_idx")

        notes4 = [f"Ласпейрес (ваги базового періоду): кошик подорожчав на {fmt((IL - 1) * 100, 2)}%.",
                  f"Пааше (ваги звітного періоду): ціни зросли на {fmt((IP - 1) * 100, 2)}%.",
                  f"Фішер (середнє геометричне): {fmt((IF - 1) * 100, 2)}% — компромісна оцінка інфляції."]
        if IL > IP + 1e-9:
            notes4.append("I_L > I_P: споживачі скоротили частку товарів, що найбільше подорожчали (ефект заміщення). "
                          "Ласпейрес дещо завищує інфляцію, Пааше — занижує; істинна оцінка — між ними.")
        elif IL < IP - 1e-9:
            notes4.append("I_L < I_P — нетипова ситуація: обсяги змістилися до товарів, що дорожчали швидше. "
                          "Перевірте вихідні дані й поясніть причину.")
        else:
            notes4.append("I_L = I_P: структура споживання не змінилася.")
        st.success("**Висновки**\n\n" + "\n".join(f"- {x}" for x in notes4))

        with st.expander("🧮 Проміжні розрахунки"):
            step = pd.DataFrame({"Товар": d["Товар"], "P₀·Q₀": d.P0 * d.Q0, "P₁·Q₀": d.P1 * d.Q0,
                                 "P₀·Q₁": d.P0 * d.Q1, "P₁·Q₁": d.P1 * d.Q1,
                                 "Зміна ціни, %": (d.P1 / d.P0.replace(0, np.nan) - 1) * 100})
            tot = pd.DataFrame([["Разом", step.iloc[:, 1].sum(), step.iloc[:, 2].sum(), step.iloc[:, 3].sum(),
                                 step.iloc[:, 4].sum(), np.nan]], columns=step.columns)
            stretch(st.dataframe, pd.concat([step, tot], ignore_index=True).round(2), hide_index=True)
        r4 = dict(ok=True, df=d, IL=IL, IP=IP, IF=IF, notes=notes4)
    report["s4"] = r4

# ════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА 5. ДИНАМІКА ІНФЛЯЦІЇ В УКРАЇНІ
# ════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.header("5. Динаміка інфляції в Україні")
    all_years = UA_DATA["Рік"].tolist()
    y_a, y_b = st.select_slider("Період (роки)", options=all_years, value=(all_years[0], all_years[-1]))
    show_rate = st.checkbox("Показати облікову ставку НБУ", value=True)
    sel = UA_DATA[(UA_DATA["Рік"] >= y_a) & (UA_DATA["Рік"] <= y_b)].reset_index(drop=True)

    prelim = (sel["Дані"] == "попередні").tolist()
    fig = go.Figure(go.Bar(
        x=sel["Рік"].astype(str), y=sel["Інфляція, %"], name="Інфляція, %",
        marker=dict(color=["#a5d6a7" if p else "#2e7d32" for p in prelim],
                    pattern=dict(shape=["/" if p else "" for p in prelim])),
        text=[fmt(v, 1) for v in sel["Інфляція, %"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:.1f}%<extra>Інфляція</extra>"))
    if show_rate:
        fig.add_trace(go.Scatter(x=sel["Рік"].astype(str), y=sel["Облікова ставка, %"], name="Облікова ставка, %",
                                 mode="lines+markers", line=dict(color="#ef6c00", width=3), marker=dict(size=8),
                                 hovertemplate="%{x}: %{y:.1f}%<extra>Облікова ставка</extra>"))
    style_fig(fig, H + 10, "Інфляція та облікова ставка НБУ, %")
    fig.update_yaxes(title="%", rangemode="tozero")
    show_plot(fig, key="fig_ua")
    st.caption("Штрихування — попередні дані. " + UA_NOTE)

    final = sel[sel["Дані"] == "остаточні"]
    cum_pct = (np.prod(1 + final["Інфляція, %"] / 100) - 1) * 100 if len(final) else float("nan")
    peak = sel.loc[sel["Інфляція, %"].idxmax()]
    low = sel.loc[sel["Інфляція, %"].idxmin()]
    mc = st.columns(2)
    mc[0].metric("Середня за період", f"{fmt(sel['Інфляція, %'].mean(), 1)}%")
    mc[1].metric("Накопичений приріст цін*", f"{fmt(cum_pct, 1)}%")
    mc2 = st.columns(2)
    mc2[0].metric("Максимум", f"{fmt(peak['Інфляція, %'], 1)}%", delta=f"{int(peak['Рік'])} р.", delta_color="off")
    mc2[1].metric("Мінімум", f"{fmt(low['Інфляція, %'], 1)}%", delta=f"{int(low['Рік'])} р.", delta_color="off")
    st.caption("* Лише за роками з остаточними даними.")

    table5 = sel.copy()
    table5["Реальна ставка, в.п."] = (table5["Облікова ставка, %"] - table5["Інфляція, %"]).round(1)
    stretch(st.dataframe, table5, hide_index=True)

    csv_df = table5.copy()
    csv_df["Накопичений індекс цін (початок періоду = 100)"] = (np.cumprod(1 + csv_df["Інфляція, %"] / 100) * 100).round(1)
    csv_df["Примітка"] = UA_NOTE
    csv_bytes = csv_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    stretch(st.download_button, "⬇️ Завантажити зведений звіт (CSV)", data=csv_bytes,
            file_name=f"inflation_ua_{y_a}_{y_b}.csv", mime="text/csv", key="dl_csv")
    st.caption("CSV: роздільник «;», кодування UTF-8 — відкривається в Excel без налаштувань.")

    notes5 = [f"Пік інфляції за період — {int(peak['Рік'])} р. ({fmt(peak['Інфляція, %'], 1)}%).",
              f"Мінімум — {int(low['Рік'])} р. ({fmt(low['Інфляція, %'], 1)}%).",
              f"Середній рівень за {y_a}–{y_b} рр. — {fmt(sel['Інфляція, %'].mean(), 1)}%."]
    for n in notes5:
        st.write("• " + n)
    report["s5"] = dict(df=table5, notes=notes5)

# ════════════════════════════════════════════════════════════════════════════
# ЕКСПОРТ У PDF
# ════════════════════════════════════════════════════════════════════════════
st.divider()
st.header("📄 Експорт результатів у PDF")
SECTION_LIST = ["1. Види інфляції", "2. Причини та механізм", "3. Реформи 90-х", "4. Індекси цін",
                "5. Динаміка в Україні"]

if not REPORTLAB_OK:
    st.error("Для експорту в PDF встановіть бібліотеку: `pip install reportlab`, а потім перезапустіть додаток.")
else:
    st.caption("Звіт відображає поточні значення всіх вкладок. Після зміни даних сформуйте PDF повторно.")
    ec = st.columns(2)
    author = ec[0].text_input("Прізвище та ім'я", placeholder="Іваненко Марія")
    group = ec[1].text_input("Група / курс", placeholder="Е-21")
    chosen = st.multiselect("Розділи, що потрапляють у звіт", SECTION_LIST, default=SECTION_LIST)
    concl = st.text_area("Власні висновки (необов'язково)", height=110,
                         placeholder="Сформулюйте 2–3 речення: що показали розрахунки та як це пов'язано з агросектором.")

    if stretch(st.button, "🧾 Сформувати PDF", key="b_pdf", type="primary"):
        if not chosen:
            st.warning("Оберіть хоча б один розділ.")
        else:
            try:
                with st.spinner("Формую PDF…"):
                    ss["pdf_bytes"] = build_pdf(report, [s for s in SECTION_LIST if s in chosen], author, group, concl)
                    ss["pdf_name"] = f"inflation_report_{datetime.now():%Y%m%d_%H%M}.pdf"
            except Exception as e:
                ss["pdf_bytes"] = None
                st.error("Не вдалося сформувати PDF. Імовірно, немає шрифту з кирилицею й інтернету для його завантаження. "
                         "Встановіть DejaVu Sans (Linux: `sudo apt install fonts-dejavu-core`; Streamlit Cloud: "
                         "додайте у packages.txt рядок fonts-dejavu-core).")
                st.caption(f"Технічна деталь: {e}")

    if ss.get("pdf_bytes"):
        st.success("PDF готовий — завантажте файл нижче.")
        stretch(st.download_button, "⬇️ Завантажити PDF", data=ss["pdf_bytes"], file_name=ss["pdf_name"],
                mime="application/pdf", key="dl_pdf")

st.caption("© Навчальний матеріал для дисципліни «Гроші та кредит». Дані: Держстат, НБУ.")
