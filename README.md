# IELTS Center System

IELTS markazi uchun professional tizim - bir martalik parol bilan kirish, kategoriyalangan video darslar va testlar.

## Texnologiyalar

- Django 4.2.16
- Django REST Framework
- Bootstrap 5
- HTMX
- Alpine.js
- SQLite (development)

## O'rnatish

1. Virtual environment yaratish:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. Paketlarni o'rnatish:
```bash
pip install -r requirements.txt
```

3. Migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Superuser yaratish:
```bash
python manage.py createsuperuser
```

5. Server ishga tushirish:
```bash
python manage.py runserver
```

## Foydalanish

### Admin Panel

1. `/admin/` ga kirish
2. Superuser bilan login qilish
3. Foydalanuvchi yaratish:
   - Users > Add User
   - Foydalanuvchi yaratilgandan keyin, UserOTP avtomatik yaratiladi
   - OTP kodni ko'rish va foydalanuvchiga berish

### Foydalanuvchi

1. `/accounts/login/` ga kirish
2. Username va OTP kodni kiritish
3. Dashboard'da video darslar va testlarni ko'rish
4. Test ishlash va natijalarni ko'rish

## Struktura

- `accounts/` - Authentication (OTP login)
- `core/` - Asosiy funksiyalar (videos, tests, profile)
- `templates/` - HTML templatelar
- `static/` - CSS, JS fayllar

## Features

- ✅ Bir martalik parol (OTP) tizimi
- ✅ Kategoriyalangan video darslar (YouTube)
- ✅ Kategoriyalangan testlar (Reading, Writing, Listening)
- ✅ Test ishlash (bir vaqtda 1 savol)
- ✅ Natijalarni saqlash va ko'rsatish
- ✅ Video progress tracking
- ✅ Foydalanuvchi profili
- ✅ Admin paneli
- ✅ HTMX bilan page refresh qilmasdan ishlash

## Admin Panel Features

- Foydalanuvchilar boshqaruvi
- OTP kod generatsiya
- Testlar va videolar boshqaruvi
- Statistikalar
- Export/Import funksiyalari

