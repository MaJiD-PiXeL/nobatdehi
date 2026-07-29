# قرارداد API

همهٔ endpointها زیر `/api/v1/` هستند، JSON برمی‌گردانند و در صورت نیاز از هدر `Authorization: Bearer <access-token>` استفاده می‌کنند. مستند زنده در `/api/schema/swagger-ui/` و OpenAPI در `/api/schema/` قابل دسترسی است.

| حوزه | مسیر | روش | مجوز | نتیجهٔ اصلی |
| --- | --- | --- | --- | --- |
| احراز هویت | `/auth/register/` | POST | عمومی | کاربر و access/refresh token |
| احراز هویت | `/auth/login/` | POST | عمومی | access/refresh token |
| کسب‌وکار | `/businesses/` | GET, POST | خواندن عمومی / کاربر | فهرست یا ثبت کسب‌وکار |
| کاتالوگ عمومی | `/businesses/{slug}/booking_catalog/` | GET | عمومی | شعبه، خدمت و کارمند فعال برای آغاز رزرو |
| شعبه | `/branches/` | CRUD | عضو tenant | شعبه‌های tenant فعال |
| خدمات | `/services/` | CRUD | عضو tenant | خدمت و کارکنان/شعبه‌ها |
| کارکنان | `/employees/` | CRUD | عضو tenant | کارمند و برنامهٔ کاری |
| زمان آزاد | `/availability/` | GET | عمومی | `branch_id, service_id, date, employee_id?` → slotها |
| نوبت | `/appointments/` | GET, POST | مشتری/عضو tenant | ایجاد یا فهرست نوبت |
| نوبت | `/appointments/{id}/cancel/` | POST | صاحب نوبت/مدیر | لغو با بررسی policy |
| پرداخت | `/payments/` | GET, POST | صاحب نوبت/مدیر | تراکنش idempotent |

نمونهٔ ثبت نوبت:

```json
{
  "business_id": "uuid",
  "branch_id": "uuid",
  "service_id": "uuid",
  "employee_id": "uuid",
  "starts_at": "2026-08-01T10:00:00+03:30",
  "customer_name": "سارا رضایی",
  "customer_phone": "09120000000",
  "notes": ""
}
```

پاسخ موفق `201` شامل `id`، `tracking_code`، `ends_at` و `status` است. خطای slot اشغال‌شده `409` و ورودی نامعتبر `400` بازمی‌گردد. تمام endpointها و schemaهای کامل از OpenAPI تولید می‌شوند تا یک منبع واحد برای Frontend و mobile باشند.
