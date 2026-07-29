# نوبت — سامانهٔ رزرو و نوبت‌دهی آنلاین

پلتفرمی API-first و multi-tenant برای کلینیک، سالن، مشاور، مدرس و هر کسب‌وکار خدماتی. طراحی معماری در [docs/architecture.md](docs/architecture.md) و قرارداد آغازین API در [docs/api.md](docs/api.md) آمده است.

## اجرای محلی با Docker

```bash
cp .env.example .env
docker compose up --build
```

- API: `http://localhost:8000/api/v1/`
- مستند Swagger: `http://localhost:8000/api/schema/swagger-ui/`
- Frontend: `http://localhost:3000/`

کانتینر backend در شروع `migrate --run-syncdb` را اجرا می‌کند تا اسکلت اولیه بدون وابستگی به ابزار محلی راه بیفتد. پیش از اولین انتشار production، migrationهای versioned را با Django در CI تولید و review کنید؛ schema در کد و تست‌ها منبع حقیقت است.

## توسعهٔ Backend بدون Docker

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cd backend
python manage.py migrate --run-syncdb
python manage.py runserver
```

برای Windows از مسیر معادل `\.venv\Scripts\` استفاده کنید. برای محیط واقعی، PostgreSQL و Redis لازم هستند؛ SQLite برای کنترل هم‌زمانی رزرو مناسب نیست.

## تضمین رزرو

`BookingService` تنها مسیر ایجاد نوبت است. این سرویس داخل transaction رکورد کارمند و رزروهای هم‌پوشان را قفل می‌کند و بازه‌های buffer را نیز در تداخل در نظر می‌گیرد. محاسبهٔ زمان آزاد فقط در backend انجام می‌شود و هنگام ثبت دوباره کنترل می‌گردد.

## بررسی کیفیت

```bash
cd backend
python manage.py test
python manage.py check
```

تست‌های رزرو در `backend/appointments/tests/` سناریوهای slot، تداخل و لغو را پوشش می‌دهند. در CI باید تست concurrency علیه PostgreSQL اجرا شود.

