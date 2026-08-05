"use client";

import { FormEvent, useEffect, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1").replace(/\/$/, "");
const input = "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-teal-500 focus:ring-4 focus:ring-teal-100";

type Provider = { name: string; specialty: string };
type BusinessService = { name: string; price: string; duration_minutes: number };
type Business = { id: string; name: string; slug: string; description: string; phone: string; address: string; providers: Provider[]; services: BusinessService[] };
type Catalog = {
  business: Business;
  branches: { id: string; name: string }[];
  services: { id: string; name: string; price: string; duration_minutes: number }[];
  employees: { id: string; first_name: string; last_name: string; specialty: string }[];
};
type Slot = { employee_id: string; starts_at: string };
type Auth = { user: { first_name: string; last_name: string; phone: string | null }; tokens: { access: string } };
type Appointment = { tracking_code: string };

const tomorrow = () => {
  const result = new Date();
  result.setDate(result.getDate() + 1);
  return result.toISOString().slice(0, 10);
};
const price = (value: string) => new Intl.NumberFormat("fa-IR").format(Number(value));
const slotTime = (value: string) => new Intl.DateTimeFormat("fa-IR", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));

function readableError(payload: unknown) {
  if (typeof payload === "string") return payload;
  if (payload && typeof payload === "object") {
    return Object.entries(payload as Record<string, unknown>)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join("، ") : String(value)}`)
      .join(" | ");
  }
  return "عملیات انجام نشد. دوباره تلاش کنید.";
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) throw new Error(readableError(payload));
  return payload as T;
}

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [searching, setSearching] = useState(true);
  const [message, setMessage] = useState("");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [booking, setBooking] = useState({ branch: "", service: "", employee: "", date: tomorrow(), name: "", phone: "", notes: "" });
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [token, setToken] = useState("");
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"register" | "login">("register");
  const [auth, setAuth] = useState({ firstName: "", lastName: "", email: "", phone: "", password: "" });
  const [ownerOpen, setOwnerOpen] = useState(false);
  const [owner, setOwner] = useState({ firstName: "", lastName: "", email: "", phone: "", password: "", business: "", description: "", address: "", professional: "", specialty: "", service: "", price: "", duration: "60" });
  const [busy, setBusy] = useState(false);

  async function search(term = query) {
    setSearching(true);
    setMessage("");
    try {
      const suffix = term.trim() ? `?q=${encodeURIComponent(term.trim())}` : "";
      setBusinesses(await request<Business[]>(`/businesses/${suffix}`));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "جست‌وجو در دسترس نیست.");
    } finally {
      setSearching(false);
    }
  }

  useEffect(() => {
    const saved = window.localStorage.getItem("nobat_access_token");
    if (saved) setToken(saved);
    void search("");
    const sharedBusiness = new URLSearchParams(window.location.search).get("business");
    if (sharedBusiness) void loadCatalog(sharedBusiness);
  }, []);

  async function loadCatalog(slug: string, scrollToBooking = true) {
    setBusy(true);
    setMessage("");
    try {
      const data = await request<Catalog>(`/businesses/${slug}/booking_catalog/`);
      setCatalog(data);
      setBooking((current) => ({ ...current, branch: data.branches[0]?.id ?? "", service: data.services[0]?.id ?? "", employee: data.employees[0]?.id ?? "" }));
      setSlots([]);
      setSelectedSlot(null);
      if (scrollToBooking) window.setTimeout(() => document.getElementById("booking")?.scrollIntoView({ behavior: "smooth" }), 0);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "اطلاعات کسب‌وکار دریافت نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function chooseBusiness(business: Business) {
    const url = new URL(window.location.href);
    url.searchParams.set("business", business.slug);
    window.history.replaceState({}, "", url);
    await loadCatalog(business.slug);
  }

  async function copyBookingLink() {
    if (!catalog) return;
    const url = new URL(window.location.href);
    url.searchParams.set("business", catalog.business.slug);
    try {
      await navigator.clipboard.writeText(url.toString());
      setMessage("لینک مستقیم صفحهٔ رزرو کپی شد؛ آن را برای مشتری‌ها بفرستید.");
    } catch {
      window.prompt("این لینک را کپی کنید:", url.toString());
    }
  }

  async function getSlots() {
    if (!booking.branch || !booking.service || !booking.date) return;
    setBusy(true);
    setMessage("");
    setSelectedSlot(null);
    try {
      const employee = booking.employee ? `&employee_id=${booking.employee}` : "";
      const result = await request<{ slots: Slot[] }>(`/availability/?branch_id=${booking.branch}&service_id=${booking.service}&date=${booking.date}${employee}`);
      setSlots(result.slots);
      if (!result.slots.length) setMessage("برای این روز زمان خالی ثبت نشده است. روز یا متخصص دیگری را انتخاب کنید.");
    } catch (error) {
      setSlots([]);
      setMessage(error instanceof Error ? error.message : "زمان‌های خالی دریافت نشدند.");
    } finally {
      setBusy(false);
    }
  }

  async function saveAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = authMode === "register"
        ? await request<Auth>("/auth/register/", { method: "POST", body: JSON.stringify({ email: auth.email, phone: auth.phone, password: auth.password, first_name: auth.firstName, last_name: auth.lastName }) })
        : await request<Auth>("/auth/login/", { method: "POST", body: JSON.stringify({ identifier: auth.email, password: auth.password }) });
      window.localStorage.setItem("nobat_access_token", result.tokens.access);
      setToken(result.tokens.access);
      setAuthOpen(false);
      setBooking((current) => ({ ...current, name: current.name || `${result.user.first_name} ${result.user.last_name}`.trim(), phone: current.phone || result.user.phone || auth.phone }));
      setMessage("حساب شما آماده است. حالا نوبت را نهایی کنید.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ورود انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function saveBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setAuthOpen(true);
      setMessage("برای ثبت نهایی نوبت، ابتدا وارد حساب شوید یا ثبت‌نام کنید.");
      return;
    }
    if (!catalog || !selectedSlot) {
      setMessage("ابتدا یک زمان خالی را انتخاب کنید.");
      return;
    }
    setBusy(true);
    try {
      const result = await request<Appointment>("/appointments/", {
        method: "POST",
        body: JSON.stringify({ business: catalog.business.id, branch: booking.branch, service: booking.service, employee: selectedSlot.employee_id, starts_at: selectedSlot.starts_at, customer_name: booking.name, customer_phone: booking.phone, notes: booking.notes }),
      }, token);
      setMessage(`نوبت با موفقیت ثبت شد. کد پیگیری شما: ${result.tracking_code}`);
      setSlots((current) => current.filter((item) => item.employee_id !== selectedSlot.employee_id || item.starts_at !== selectedSlot.starts_at));
      setSelectedSlot(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ثبت نوبت انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function saveOwner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const account = await request<Auth>("/auth/register/", { method: "POST", body: JSON.stringify({ email: owner.email, phone: owner.phone, password: owner.password, first_name: owner.firstName, last_name: owner.lastName }) });
      const [firstName, ...lastName] = owner.professional.trim().split(/\s+/);
      const business = await request<Business>("/businesses/onboard/", {
        method: "POST",
        body: JSON.stringify({ business_name: owner.business, description: owner.description, phone: owner.phone, address: owner.address, professional_first_name: firstName || owner.firstName, professional_last_name: lastName.join(" "), specialty: owner.specialty, service_name: owner.service, service_price: owner.price, service_duration_minutes: Number(owner.duration) || 60 }),
      }, account.tokens.access);
      window.localStorage.setItem("nobat_access_token", account.tokens.access);
      setToken(account.tokens.access);
      setOwnerOpen(false);
      setQuery(business.name);
      setMessage(`صفحهٔ «${business.name}» ساخته شد و آمادهٔ دریافت نوبت است.`);
      await search(business.name);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ساخت کسب‌وکار انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  const selectedService = catalog?.services.find((service) => service.id === booking.service);

  return <main className="min-h-screen bg-slate-50 text-slate-900">
    <header className="border-b border-slate-200 bg-white"><div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4"><button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="text-2xl font-black text-teal-700">نوبت</button><button onClick={() => setOwnerOpen((open) => !open)} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white">ثبت کسب‌وکار</button></div></header>
    <section className="bg-gradient-to-bl from-teal-800 via-teal-700 to-cyan-700 px-5 py-20 text-center text-white"><div className="mx-auto max-w-4xl"><p className="mb-4 text-sm font-bold text-teal-100">رزرو آنلاین برای خدمات حضوری</p><h1 className="text-4xl font-black leading-tight sm:text-6xl">اسم شخص یا کسب‌وکار را جست‌وجو کنید و نوبت بگیرید.</h1><p className="mx-auto mt-6 max-w-2xl leading-8 text-teal-50">پزشک، آرایشگر، مشاور، مدرس یا هر ارائه‌دهندهٔ خدمت؛ همه در یک جست‌وجوی ساده.</p><form onSubmit={(event) => { event.preventDefault(); void search(); }} className="mx-auto mt-9 flex max-w-2xl flex-col gap-3 rounded-2xl bg-white p-3 shadow-2xl sm:flex-row"><input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 rounded-xl border-0 px-4 py-3 text-slate-900 outline-none" placeholder="مثلاً نیلوفر احمدی یا کلینیک آرامش" /><button className="rounded-xl bg-teal-600 px-6 py-3 font-bold">جست‌وجو</button></form></div></section>
    <section className="mx-auto max-w-6xl px-5 py-12"><div className="mb-6"><p className="text-sm font-bold text-teal-700">کسب‌وکارها و متخصصان</p><h2 className="text-2xl font-black">نتیجهٔ جست‌وجو</h2></div>{message && <p className="mb-5 rounded-xl bg-teal-50 p-4 text-sm font-semibold leading-6 text-teal-800">{message}</p>}{searching ? <p className="py-10 text-center text-slate-500">در حال دریافت نتایج…</p> : businesses.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500"><p>نتیجه‌ای پیدا نشد.</p><button onClick={() => setOwnerOpen(true)} className="mt-4 font-bold text-teal-700 underline">صفحهٔ کسب‌وکارتان را بسازید</button></div> : <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">{businesses.map((business) => <article key={business.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-teal-100 text-xl font-black text-teal-700">{business.name.slice(0, 1)}</div><div><h3 className="font-black">{business.name}</h3><p className="text-sm text-slate-500">{business.address || "رزرو آنلاین"}</p></div></div><p className="mt-4 text-sm leading-7 text-slate-600">{business.description || "خدمات و زمان‌های خالی را مشاهده کنید."}</p>{business.services.length > 0 && <div className="mt-4"><p className="mb-2 text-xs font-bold text-slate-500">خدمات</p><div className="flex flex-wrap gap-2">{business.services.map((service) => <span key={`${business.id}-${service.name}`} className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">{service.name} · {price(service.price)} تومان</span>)}</div></div>}{business.providers.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{business.providers.map((provider) => <span key={`${business.id}-${provider.name}`} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{provider.name}{provider.specialty ? ` · ${provider.specialty}` : ""}</span>)}</div>}<button onClick={() => void chooseBusiness(business)} disabled={busy} className="mt-6 rounded-xl bg-slate-900 px-4 py-3 text-sm font-bold text-white disabled:opacity-60">مشاهده و رزرو نوبت</button></article>)}</div>}</section>
    {catalog && <section id="booking" className="border-y border-teal-100 bg-teal-50 px-5 py-14"><div className="mx-auto max-w-5xl"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-bold text-teal-700">رزرو نوبت</p><h2 className="mt-1 text-3xl font-black">{catalog.business.name}</h2></div><button type="button" onClick={() => void copyBookingLink()} className="rounded-xl border border-teal-600 px-4 py-2 text-sm font-bold text-teal-700">کپی لینک رزرو</button></div><form onSubmit={saveBooking} className="mt-7 grid gap-6 rounded-3xl bg-white p-6 shadow-sm lg:grid-cols-[1.1fr_.9fr]"><div className="space-y-5"><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold">شعبه<select value={booking.branch} onChange={(event) => setBooking((current) => ({ ...current, branch: event.target.value }))} className={input}>{catalog.branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label><label className="text-sm font-bold">خدمت<select value={booking.service} onChange={(event) => setBooking((current) => ({ ...current, service: event.target.value }))} className={input}>{catalog.services.map((service) => <option key={service.id} value={service.id}>{service.name} · {price(service.price)} تومان</option>)}</select></label><label className="text-sm font-bold">متخصص<select value={booking.employee} onChange={(event) => setBooking((current) => ({ ...current, employee: event.target.value }))} className={input}>{catalog.employees.map((employee) => <option key={employee.id} value={employee.id}>{`${employee.first_name} ${employee.last_name}`.trim()}{employee.specialty ? ` · ${employee.specialty}` : ""}</option>)}</select></label><label className="text-sm font-bold">تاریخ<input type="date" min={tomorrow()} value={booking.date} onChange={(event) => setBooking((current) => ({ ...current, date: event.target.value }))} className={input} /></label></div><button type="button" onClick={() => void getSlots()} disabled={busy} className="rounded-xl border border-teal-600 px-5 py-3 text-sm font-bold text-teal-700 disabled:opacity-60">نمایش زمان‌های خالی</button><div className="flex flex-wrap gap-2">{slots.map((slot) => <button key={`${slot.employee_id}-${slot.starts_at}`} type="button" onClick={() => setSelectedSlot(slot)} className={`rounded-xl border px-4 py-2 text-sm font-bold ${selectedSlot?.employee_id === slot.employee_id && selectedSlot.starts_at === slot.starts_at ? "border-teal-600 bg-teal-600 text-white" : "border-slate-200 text-slate-700"}`}>{slotTime(slot.starts_at)}</button>)}</div></div><div className="rounded-2xl bg-slate-50 p-5"><h3 className="font-black">تأیید نوبت</h3><p className="mt-2 text-sm text-slate-500">{selectedService ? `${selectedService.name} · ${selectedService.duration_minutes} دقیقه` : "خدمت را انتخاب کنید."}</p><label className="mt-5 block text-sm font-bold">نام و نام خانوادگی<input required value={booking.name} onChange={(event) => setBooking((current) => ({ ...current, name: event.target.value }))} className={input} /></label><label className="mt-4 block text-sm font-bold">شماره همراه<input required value={booking.phone} onChange={(event) => setBooking((current) => ({ ...current, phone: event.target.value }))} className={input} placeholder="0912…" /></label><label className="mt-4 block text-sm font-bold">توضیحات (اختیاری)<textarea value={booking.notes} onChange={(event) => setBooking((current) => ({ ...current, notes: event.target.value }))} className={input} rows={3} /></label>{!token && <button type="button" onClick={() => setAuthOpen(true)} className="mt-5 text-sm font-bold text-teal-700 underline">ورود یا ساخت حساب مشتری</button>}<button disabled={busy} className="mt-5 w-full rounded-xl bg-teal-600 px-4 py-3 font-bold text-white disabled:opacity-60">ثبت نهایی نوبت</button></div></form></div></section>}
    {authOpen && <section className="mx-auto max-w-xl px-5 py-12"><div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-lg"><div className="flex items-center justify-between"><h2 className="text-2xl font-black">{authMode === "register" ? "ثبت‌نام مشتری" : "ورود مشتری"}</h2><button onClick={() => setAuthOpen(false)} className="text-sm text-slate-500">بستن</button></div><form onSubmit={saveAuth} className="mt-5 space-y-4">{authMode === "register" && <div className="grid gap-4 sm:grid-cols-2"><input required value={auth.firstName} onChange={(event) => setAuth((current) => ({ ...current, firstName: event.target.value }))} className={input} placeholder="نام" /><input value={auth.lastName} onChange={(event) => setAuth((current) => ({ ...current, lastName: event.target.value }))} className={input} placeholder="نام خانوادگی" /></div>}<input required type="email" value={auth.email} onChange={(event) => setAuth((current) => ({ ...current, email: event.target.value }))} className={input} placeholder="ایمیل" />{authMode === "register" && <input required value={auth.phone} onChange={(event) => setAuth((current) => ({ ...current, phone: event.target.value }))} className={input} placeholder="شماره همراه" />}<input required minLength={authMode === "register" ? 10 : undefined} type="password" value={auth.password} onChange={(event) => setAuth((current) => ({ ...current, password: event.target.value }))} className={input} placeholder="گذرواژه" /><button disabled={busy} className="w-full rounded-xl bg-slate-900 py-3 font-bold text-white disabled:opacity-60">{authMode === "register" ? "ساخت حساب و ادامه" : "ورود و ادامه"}</button></form><button onClick={() => setAuthMode((mode) => mode === "register" ? "login" : "register")} className="mt-4 text-sm font-bold text-teal-700">{authMode === "register" ? "حساب دارید؟ وارد شوید" : "حساب ندارید؟ ثبت‌نام کنید"}</button></div></section>}
    {ownerOpen && <section className="border-t border-slate-200 bg-slate-100 px-5 py-14"><div className="mx-auto max-w-3xl rounded-3xl bg-white p-6 shadow-xl"><div className="flex justify-between gap-4"><div><p className="text-sm font-bold text-teal-700">برای صاحبان کسب‌وکار</p><h2 className="mt-1 text-3xl font-black">صفحهٔ رزرو خودتان را بسازید</h2><p className="mt-2 text-sm leading-6 text-slate-500">حساب، صفحهٔ کسب‌وکار، اولین خدمت، متخصص و ساعت کاری ۹ تا ۱۷ به‌صورت خودکار ساخته می‌شود.</p></div><button onClick={() => setOwnerOpen(false)} className="text-sm text-slate-500">بستن</button></div><form onSubmit={saveOwner} className="mt-7 grid gap-4 sm:grid-cols-2"><input required value={owner.firstName} onChange={(event) => setOwner((current) => ({ ...current, firstName: event.target.value }))} className={input} placeholder="نام مالک" /><input value={owner.lastName} onChange={(event) => setOwner((current) => ({ ...current, lastName: event.target.value }))} className={input} placeholder="نام خانوادگی مالک" /><input required type="email" value={owner.email} onChange={(event) => setOwner((current) => ({ ...current, email: event.target.value }))} className={input} placeholder="ایمیل" /><input required value={owner.phone} onChange={(event) => setOwner((current) => ({ ...current, phone: event.target.value }))} className={input} placeholder="شماره همراه" /><input required minLength={10} type="password" value={owner.password} onChange={(event) => setOwner((current) => ({ ...current, password: event.target.value }))} className={input} placeholder="گذرواژه" /><input required value={owner.business} onChange={(event) => setOwner((current) => ({ ...current, business: event.target.value }))} className={input} placeholder="نام کسب‌وکار" /><input required value={owner.professional} onChange={(event) => setOwner((current) => ({ ...current, professional: event.target.value }))} className={input} placeholder="نام متخصص یا ارائه‌دهندهٔ خدمت" /><input value={owner.specialty} onChange={(event) => setOwner((current) => ({ ...current, specialty: event.target.value }))} className={input} placeholder="تخصص" /><input required value={owner.service} onChange={(event) => setOwner((current) => ({ ...current, service: event.target.value }))} className={input} placeholder="اولین خدمت" /><input required inputMode="numeric" value={owner.price} onChange={(event) => setOwner((current) => ({ ...current, price: event.target.value }))} className={input} placeholder="قیمت به تومان" /><input value={owner.duration} onChange={(event) => setOwner((current) => ({ ...current, duration: event.target.value }))} className={input} placeholder="مدت خدمت به دقیقه" /><input value={owner.address} onChange={(event) => setOwner((current) => ({ ...current, address: event.target.value }))} className={input} placeholder="آدرس (اختیاری)" /><textarea value={owner.description} onChange={(event) => setOwner((current) => ({ ...current, description: event.target.value }))} className={`${input} sm:col-span-2`} rows={3} placeholder="معرفی کوتاه (اختیاری)" /><button disabled={busy} className="rounded-xl bg-teal-600 px-5 py-3 font-bold text-white disabled:opacity-60 sm:col-span-2">ساخت صفحه و فعال‌کردن رزرو</button></form></div></section>}
    <footer className="px-5 py-8 text-center text-sm text-slate-500">نوبت · جست‌وجو، انتخاب زمان و رزرو آنلاین</footer>
  </main>;
}
