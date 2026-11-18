# Breast-Cancer-Detection-ML
Classification of breast cancer tumors using 7 machine learning algorithms (WDBC dataset).
# پروژه تشخیص تومور پستان با یادگیری ماشین (WDBC)

این مخزن پیاده‌سازی هفت الگوریتم اسلاید ۱۷۸ برای طبقه‌بندی تومور به دو کلاس **بدخیم (Malignant)** و **خوش‌خیم (Benign)** را ارائه می‌کند:

1. Naive Bayes
2. K-Nearest Neighbors (KNN)
3. Decision Tree
4. Random Forest
5. Support Vector Machine (SVM)
6. Logistic Regression
7. Artificial Neural Network (ANN / MLP)

> **محدودیت مهم:** این پروژه صرفاً آموزشی و پژوهشی است و برای تشخیص، غربالگری یا تصمیم درمانی پزشکی طراحی یا اعتبارسنجی نشده است.

## داده‌ها

از نسخهٔ همراه scikit-learn از مجموعه‌دادهٔ **Wisconsin Breast Cancer Diagnostic (WDBC)** استفاده می‌شود: ۵۶۹ نمونه، ۳۰ ویژگی عددی و دو کلاس (۲۱۲ بدخیم و ۳۵۷ خوش‌خیم). ویژگی‌های اصلی از تصویر دیجیتال نمونهٔ آسپیراسیون با سوزن ظریف (FNA) استخراج شده‌اند. فایل CSV داده نیز در `data/wdbc_dataset.csv` قرار دارد.

منبع اصلی: [UCI Machine Learning Repository – WDBC](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic)

## روش آزمایش

- تقسیم آموزش/آزمون: ۸۰٪/۲۰٪ با نمونه‌گیری طبقه‌بندی‌شده و `random_state=42`.
- تنظیم حساسیت پارامترها: اعتبارسنجی متقاطع طبقه‌بندی‌شدهٔ ۵ بخشی فقط روی بخش آموزش.
- انتخاب ویژگی: انتخاب ۲۰ ویژگی از ۳۰ ویژگی با `SelectKBest(f_classif)`؛ این مرحله داخل Pipeline است تا در هر fold فقط روی دادهٔ آموزش همان fold برازش شود.
- استانداردسازی: برای Naive Bayes، KNN، SVM، Logistic Regression و ANN؛ برای درخت تصمیم و جنگل تصادفی لازم نیست.
- معیار انتخاب تنظیم نهایی: بیشترین میانگین حساسیت (Recall برای کلاس بدخیم)، سپس F1 و در صورت تساوی ROC-AUC.
- مجموعهٔ آزمون تا ارزیابی نهایی کنار گذاشته می‌شود و در تنظیم پارامترها نقشی ندارد.

در تمام معیارهای دودویی، کلاس مثبت **بدخیم** است. بنابراین Sensitivity نرخ شناسایی نمونه‌های بدخیم و Specificity نرخ شناسایی نمونه‌های خوش‌خیم است.

## اجرا

Python 3.10 یا جدیدتر پیشنهاد می‌شود.

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
python src/train_models.py
python src/build_report.py
