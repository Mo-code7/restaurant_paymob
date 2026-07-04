# 🍽️ Restaurant PayMob Integration - Odoo 19

موديول متكامل لإدارة طلبات المطعم مع بوابة الدفع PayMob.

---

## ✅ المميزات

- **إدارة الطلبات** بحالات واضحة (جديد → مؤكد → تحضير → جاهز → مدفوع → مكتمل)
- **PayMob Integration** كاملة بالـ 3 خطوات الرسمية
- **Webhook** لتأكيد الدفع أوتوماتيك مع HMAC verification
- **Kanban View** لمتابعة الطلبات في الكيتشن
- **أصناف الطلب** مع حساب الضرائب تلقائياً
- **Chatter** لتتبع كل تغيير في الطلب

---

## ⚙️ إعداد PayMob

### 1. الحصول على البيانات من PayMob Dashboard

| البيانات | المكان في Dashboard |
|----------|---------------------|
| API Key | Settings > Account Info > API Key |
| Integration ID | Settings > Integrations > Online Card |
| iFrame ID | Settings > iFrames |
| HMAC Secret | Settings > Account Info > HMAC Secret |

### 2. إعداد أوديو

اذهب إلى: **الإعدادات > PayMob للمطعم**
واملأ الحقول الأربعة.

### 3. إعداد Webhook في PayMob

في لوحة تحكم PayMob، اذهب إلى:
**Settings > Integrations > [Integration] > Transaction Processed Callback**

اضبط الـ URL:
```
https://yourdomain.com/paymob/webhook
```

---

## 🚀 طريقة الاستخدام

1. افتح **المطعم > الطلبات**
2. أنشئ طلب جديد واختر العميل والأصناف
3. اضغط **"تأكيد الطلب"**
4. اضغط **"💳 ادفع بـ PayMob"** → هيفتح صفحة الدفع
5. بعد الدفع، الـ Webhook هيحدّث الطلب أوتوماتيك ✅

---

## 🗂️ هيكل الملفات

```
restaurant_paymob/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── restaurant_order.py       # النموذج الرئيسي + PayMob logic
│   ├── restaurant_order_line.py  # أصناف الطلب
│   └── res_config_settings.py    # إعدادات PayMob
├── controllers/
│   ├── __init__.py
│   └── paymob_webhook.py         # استقبال تأكيد الدفع
├── views/
│   ├── restaurant_order_views.xml
│   ├── res_config_settings_views.xml
│   └── menu_views.xml
├── data/
│   └── sequence_data.xml
└── security/
    └── ir.model.access.csv
```

---

## 🔒 الأمان

- كل الـ API Keys متخزنة في `ir.config_parameter` (مش في الكود)
- الـ Webhook بيعمل HMAC verification عشان يتأكد إن الريكوست جاية من PayMob فعلاً
- الـ Webhook route مش محتاج authentication (`auth='public'`) عشان PayMob تقدر توصله

---

## 📞 دعم

للمساعدة أو التطوير، تواصل مع فريق التطوير.
