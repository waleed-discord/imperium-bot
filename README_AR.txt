تشغيل بوتات Discord الأربعة على macOS

1) ثبّت Python 3.11 أو أحدث وFFmpeg: brew install ffmpeg
2) من Terminal ادخل مجلد الملفات ثم أنشئ بيئة افتراضية:
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   pip install -r requirements.txt
3) انسخ .env.example إلى ملف اسمه .env، ثم ضع التوكنات الجديدة لكل بوت ومفتاح TMDB الجديد إن احتجته. لا تشارك ملف .env.
4) شغّل كل بوت في نافذة Terminal مستقلة:
   python bot1.py
   python bot2.py
   python bot3.py
   python bot4.py

ملاحظات أمنية ووظيفية:
- تم حذف بيانات الدخول المكشوفة من الأكواد واستبدالها بمتغيرات .env. ألغِ التوكنات القديمة وولّد توكنات جديدة من Discord Developer Portal، وبدّل مفتاح TMDB المنشور.
- البوت الأول هو نسخة الوظائف الإضافية (التذاكر واللوقات وترشيحات الأفلام والمسلسلات). اختبر هذه الوظائف وصلاحيات Discord بعد التشغيل.
- شغّل كل بوت في عملية منفصلة؛ لا تشغّل نفس الملف مرتين بالتوكن نفسه.
- بعض وظائف النسخ الأصلية قد تحتاج مراجعة صلاحيات السيرفر وDeveloper Portal (Message Content Intent وServer Members Intent).
