#!/bin/bash
echo "🚀 بدء تشغيل بوت MN.Py..."
echo "🔧 تثبيت المتطلبات الإضافية..."

# تثبيت المتطلبات الأساسية
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ تم تثبيت المتطلبات بنجاح"
python mn.py
