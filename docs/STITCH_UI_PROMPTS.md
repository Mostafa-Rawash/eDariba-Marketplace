# eDariba Marketplace — Google Stitch Prompts

How to use:
1. Start a new Stitch project (Web, desktop 1440).
2. Paste **Prompt 0 (Design System)** first.
3. Then paste **one screen prompt at a time** (1 → 12). After each screen, ask Stitch for the mobile version with the line given at the end of each prompt.
4. If Stitch drifts (wrong font, gold, left-to-right layout, emoji), paste the "Correction prompt" at the bottom of this file.

Scope. The public Marketplace pages on edariba.com (home, directories, profile, service, project, search) already exist from earlier Stitch comps. These prompts cover:
- **A.** The new logged-in Marketplace workspace inside the eDariba app (app.edariba.com). This is the main work.
- **B.** The two public pieces that change: the request button on the accountant profile, and the sign-in gate.

All sample names, companies and numbers below are fictional placeholders.

---

## Prompt 0 — Design System (paste first)

```
You are designing screens for "eDariba" (إي ضريبة), an Arabic-first Egyptian tax and e-invoicing SaaS. We are adding a professional Marketplace: business owners find certified accountants, request services, and track requests; accountants manage their public profile, their services, and incoming requests; freelancers send proposals on projects.

LANGUAGE & DIRECTION
- Every screen is fully Arabic, right-to-left (dir="rtl"). Sidebar on the RIGHT. Text right-aligned. Back arrows point right. Progress and timelines flow right to left.
- Numbers use Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩). Currency is written after the number: "١,٨٠٠ ج.م".
- Emails and phone numbers are shown left-to-right inside their fields.

TYPOGRAPHY (only these two fonts, nothing else)
- Headings and numerals: "IBM Plex Sans Arabic", weights 500/600/700.
- Body, labels, inputs, buttons: "Tajawal", weights 400/500/700.
- Never use Inter, Roboto, Cairo, Almarai, Amiri or any other font. Normal letter-spacing for Arabic (never tight).
- Scale: page title 32px/700, section title 20–24px/700, body 16px/1.75, label 14px/600, caption 12–13px.

COLOR TOKENS
- teal (primary brand green): #203524
- teal-deep: #15251A
- teal-mid: #33543A
- teal-light: #4C9E50
- teal-muted (soft green fill): #E0EED9
- teal-wash: #E4F0DE
- matcha (the ONLY accent): #D1F470, hover #A1D78F. Use it only as a FILL (buttons, active pills, small dots), never as text on white.
- canvas (page background): #F8FAF4
- surface (cards): #FFFFFF
- ink (text): #11110D
- muted text: #68737D
- border (hairlines): #E1E2DE
- success #4CAF50, warning #FFC107, danger #D32F2F (status only, small amounts)
- NO gold, NO purple, NO blue gradients, NO beige/cream page background.

SHAPE & DEPTH
- Cards: white, 1px #E1E2DE border, radius 24px, padding 24–32px, very soft shadow (0 2px 8px rgba(0,0,0,0.04)).
- Inputs: white, 1px border #E1E2DE, radius 10px, 44–48px tall, green focus ring (3px soft green glow).
- ALL buttons are full pills (radius 999px), 48px tall:
  • Primary on light = matcha fill + teal-deep text.
  • Secondary = teal fill + white text.
  • Ghost = transparent + 1px border + ink text.
  • Destructive = white with danger text and border.
- Status pills: radius 999px, 4px 12px, 12px/700 text.
- Dark punctuation panels (#203524, radius 40px) are allowed at most once per screen, for a highlight block only.
- No left/right colored border stripes on cards. No emoji. Icons are thin outlined line icons (Lucide style, 1.75px stroke, 20px).

APP SHELL (used on every logged-in screen)
- Right sidebar 280px, white, hairline left border. Logo "إي ضريبة" at top. Grouped nav with small grey group labels.
- Active item: teal-muted background, teal text, 4px teal bar on its right edge.
- Existing groups (show them collapsed-looking, normal): الرئيسية، الفواتير والإيصالات، التقارير الضريبية، العملاء والمنتجات، الإعدادات.
- NEW group "السوق" with items: الطلبات (with a small matcha count badge "٣"), ملفي المهني, خدماتي, عروضي, مشروعاتي.
- Top header 72px, white, hairline bottom: page breadcrumb on the right; on the left a notification bell with a dot, a company/workspace switcher pill ("شركة النيل للتجارة ▾") and a round avatar.
- Content area on canvas #F8FAF4 with 32px padding, max width 1200px.

TONE
- Calm, direct, respectful. Short labels. Errors say what happened and how to fix it. Empty states give one clear next action.
- Editorial hierarchy on every page: small eyebrow label (14px/700, teal-mid) → big title → one-line description → content.

Confirm the system, then wait for the screen prompts.
```

---

## A. Logged-in Marketplace workspace (app.edariba.com)

### Prompt 1 — Requests inbox `/marketplace/requests`

```
Design the "Requests" inbox screen inside the app shell (sidebar item "الطلبات" active).

Header block:
- Eyebrow "السوق المهني"
- Title "الطلبات"
- Description "تابع الطلبات التي أرسلتها للمحاسبين والطلبات التي وصلتك من العملاء في مكان واحد."
- Primary matcha pill button on the left: "ابحث عن محاسب" with an external-link icon (opens edariba.com/marketplace).

Segmented tabs (pill segmented control, active = teal fill white text):
- "الواردة ٧" (requests clients sent to me, shown only to accountants)
- "المُرسلة ٤" (requests I sent)

Stat row: 4 compact white stat cards, numeral first in IBM Plex 700 32px, label under it in muted 13px:
- "٣" جديدة
- "٢" بانتظار ردك
- "١٢" تم الرد
- "٥" مغلقة

Filter bar (single white card row):
- Search input "ابحث باسم العميل أو نص الطلب"
- Status dropdown "كل الحالات"
- Service-type dropdown "كل أنواع الخدمات" (options: فحص ضريبي أو طعن، تفعيل الفاتورة/الإيصال الإلكتروني، الإقرار الضريبي السنوي، استشارة مالية وتخطيط ضريبي)
- Date dropdown "آخر ٣٠ يومًا"

Table in a white card (header row on teal-muted, 14px/600). Columns, right to left:
1. العميل: avatar circle with initial + name + small company line
2. نوع الخدمة
3. الخدمة المرتبطة: muted text or "—"
4. ملخص الطلب: one line, truncated
5. الحالة: status pill
6. تاريخ الإرسال
7. Row action: ghost pill "عرض"

Status pill colors:
- جديد = matcha fill, teal-deep text
- تم الرد = teal-muted fill, teal text
- مقبول = soft green (success 15%) with green text
- مرفوض = soft red with danger text
- ملغي = grey fill, muted text
- مغلق = white with border and muted text
Unread rows have a small 8px matcha dot before the client name and bold text.

Sample rows (6):
- أحمد سمير / شركة النيل للتجارة، فحص ضريبي أو طعن، "باقة فحص ضريبي ٢٠٢٣"، "وصلنا إخطار فحص عن سنة ٢٠٢٢ ومحتاجين نجهز الرد قبل…"، جديد، منذ ساعتين
- منى عادل / مكتب منى للاستيراد، تفعيل الفاتورة الإلكترونية، —، "عايزين نربط السيستم بتاعنا بمنظومة الفاتورة…"، تم الرد، أمس
- … plus 4 more varied statuses.

Footer: compact pill pagination "١ ٢ ٣ ›" and "عرض ١–٦ من ١١".

Then show the SAME screen in the "المُرسلة" tab: column 1 becomes "المحاسب" (avatar + name + "محاسب قانوني معتمد" with a small verified check icon), and the row action is "متابعة".

Mobile follow-up: "Now the mobile version (390px): sidebar becomes a bottom sheet menu, stats become a 2×2 grid, table becomes stacked cards with the status pill at the top-left."
```

### Prompt 2 — Requests inbox: empty, loading and error states

```
Create 4 state variants of the Requests inbox body (keep the app shell and header block):
1. EMPTY "الواردة" for a new accountant: centered white card, simple abstract geometric illustration (green lines and circles, no people), title "لا توجد طلبات واردة بعد", text "عندما يرسل لك عميل طلبًا من دليل المحاسبين سيظهر هنا وسنرسل لك بريدًا إلكترونيًا.", matcha button "أكمل ملفك المهني", ghost button "معاينة ملفي العام".
2. EMPTY "المُرسلة": title "لم ترسل أي طلب بعد", text "ابحث عن محاسب معتمد في تخصصك وأرسل له طلبك في دقيقة.", matcha button "تصفح دليل المحاسبين".
3. LOADING: skeleton stat cards and 5 skeleton table rows in light grey (#EFEFEA) shimmer. No spinners, no toasts.
4. ERROR: inline alert card at the top with a danger-colored outline icon, title "تعذر تحميل الطلبات", text "تحقق من اتصالك بالإنترنت ثم أعد المحاولة.", ghost button "إعادة المحاولة". The rest of the page is visible but dimmed.
```

### Prompt 3 — Send a request form `/marketplace/request/new`

```
Design the "Send a request" screen. The user arrives here from the public accountant profile on edariba.com, sometimes right after signing in. App shell is visible; the sidebar item "الطلبات" is active. Breadcrumb: "السوق ← الطلبات ← طلب جديد".

Layout: two columns on desktop. The form is the wide column (8/12, right side); a sticky summary card is the narrow column (4/12, left side).

Top: a slim success-tinted strip (teal-wash background, radius 16px) with a check icon: "تم تسجيل دخولك بنجاح — أكمل طلبك إلى أ. محمود الشريف". Show it as dismissible.

Summary card (left column, white, radius 24px):
- Avatar 64px, name "أ. محمود الشريف", verified badge pill "معتمد من إي ضريبة" (teal-muted).
- Headline "محاسب قانوني — متخصص في الفحص الضريبي والقيمة المضافة".
- Location "القاهرة — مدينة نصر" and "١٤ سنة خبرة".
- Specialty chips (pill-persona style): "فحص ضريبي"، "قيمة مضافة"، "فاتورة إلكترونية".
- If a service was chosen: a nested service mini-card with thumbnail, title "مراجعة الإقرار الضريبي قبل التقديم", price "١,٨٠٠ ج.م — إجمالي". Its top edge has a 3px full-width gradient bar from #203524 to #D1F470 (the only allowed accent bar).
- Ghost link "عرض الملف العام" with an external-link icon.

Form card (right column), title "تفاصيل طلبك", 3 sections separated by hairlines:

Section 1 "الخدمة المطلوبة"
- Radio cards (2×2 grid, selectable, selected = teal border 2px + teal-muted fill + check):
  فحص ضريبي أو طعن مستعجل / تفعيل الفاتورة أو الإيصال الإلكتروني / تقديم الإقرار الضريبي السنوي / استشارة مالية وتخطيط ضريبي عام
- Select "الخدمة المرتبطة (اختياري)", preselected "مراجعة الإقرار الضريبي قبل التقديم".

Section 2 "اشرح موقفك"
- Textarea, 6 rows, label "موجز الطلب *", placeholder "اذكر بإيجاز سنة الفحص، مأمورية الضرائب المختصة، أو الخدمة المراد تنفيذها…", character counter "٠ / ١٠٠٠" on the left.
- Helper with a lock icon: "لا تكتب كلمات مرور أو بيانات بنكية. المحاسب سيتواصل معك لطلب أي مستندات."

Section 3 "بيانات التواصل" (prefilled from the account, shown as read-only rows with a small "تعديل" text link):
- الاسم: أحمد سمير
- المنشأة: شركة النيل للتجارة
- البريد الإلكتروني: ahmed@nile-trading.com (LTR)
- Editable input "رقم الهاتف أو واتساب *": 01xxxxxxxxx (LTR)

Consent checkbox: "أوافق على مشاركة بيانات التواصل هذه مع المحاسب لهذا الطلب فقط."

Action bar at the bottom of the card: matcha primary pill "إرسال الطلب" with a send icon, ghost pill "إلغاء". Under it, muted 13px: "سيصلك إشعار بالبريد عند رد المحاسب، ويمكنك متابعة الطلب من صفحة الطلبات."

Also show field validation on one field: the textarea with a danger border, light pink wash, and the message "اكتب ٢٠ حرفًا على الأقل حتى يفهم المحاسب طلبك."

Mobile follow-up: "Mobile 390px: the summary card collapses into a compact horizontal card at the top; the action bar becomes a sticky bottom bar."
```

### Prompt 4 — Request sent confirmation + unavailable provider

```
Design 2 states of the Send-request screen:

A) SUCCESS (replaces the form): centered white card, radius 24px. A large circular matcha badge with a teal check (subtle draw-in feel). Title "تم إرسال طلبك بنجاح". Text "أرسلنا طلبك إلى أ. محمود الشريف وأبلغناه بالبريد الإلكتروني. ستجد الرد في صفحة الطلبات." A small receipt box (teal-wash, radius 16px) with rows: رقم الطلب "MR-٢٠٤٨"، نوع الخدمة، تاريخ الإرسال، الحالة pill "جديد". Buttons: teal pill "متابعة الطلب", ghost pill "العودة لدليل المحاسبين". Under them, a "what happens next" 3-step horizontal timeline (right to left): "استلام الطلب" (done) → "رد المحاسب" (pending) → "الاتفاق على التنفيذ" (pending).

B) PROVIDER UNAVAILABLE: same layout; muted illustration of an abstract closed folder; title "هذا الملف غير متاح حاليًا"; text "ربما قام المحاسب بإيقاف ملفه مؤقتًا. يمكنك اختيار محاسب آخر بنفس التخصص."; matcha button "محاسبون بنفس التخصص"; below it 3 compact accountant suggestion cards (avatar, name, specialty chips, small ghost "إرسال طلب").
```

### Prompt 5 — Request detail, accountant view `/marketplace/requests/:id`

```
Design the request detail screen as seen by the ACCOUNTANT (recipient). Breadcrumb "السوق ← الطلبات ← MR-٢٠٤٨".

Header row: title "فحص ضريبي عن سنة ٢٠٢٢", status pill "جديد" (matcha), muted "أُرسل منذ ساعتين". On the left: a status dropdown pill "تغيير الحالة ▾" and a ghost icon button "⋯".

Two columns:

RIGHT (8/12):
1. "تفاصيل الطلب" card:
   - Rows: نوع الخدمة، الخدمة المرتبطة (link)، تاريخ الإرسال.
   - The request text in a soft canvas box, 16px/1.75: "وصلنا إخطار فحص عن سنة ٢٠٢٢ من مأمورية ضرائب مدينة نصر، ومحتاجين نجهز المستندات والرد قبل ميعاد الجلسة الشهر الجاي…"
2. "سجل الطلب" activity timeline (vertical, line on the right, small round nodes):
   - "أرسل أحمد سمير الطلب" — منذ ساعتين
   - "تم إرسال إشعار بريدي إليك" — منذ ساعتين
   Nodes: teal for events, matcha for the latest.
3. "ردك على العميل" composer card:
   - Textarea placeholder "اكتب ردك: موعد مقترح للتواصل، المستندات المطلوبة، والتكلفة التقديرية…"
   - Quick-insert chips: "طلب مستندات"، "اقتراح موعد مكالمة"، "عرض سعر مبدئي"
   - Actions: matcha pill "إرسال الرد", ghost pill "رفض الطلب" (danger text)
   - Muted hint: "سيصل ردك للعميل بالبريد الإلكتروني وسيظهر في حسابه."

LEFT (4/12), sticky:
- "بيانات العميل" card: avatar, name, company "شركة النيل للتجارة", email (LTR) with copy icon, phone (LTR) with a WhatsApp-style outline icon and copy icon. Small privacy note: "بيانات التواصل مرئية لك بسبب هذا الطلب فقط."
- "الخطوات التالية" mini checklist: "راجع الطلب" ✓, "أرسل ردك", "اتفق على التنفيذ".

Also show the "رفض الطلب" confirmation modal: drawer-style panel sliding from the right, max 560px, backdrop blur. Title "رفض الطلب؟". Optional reason select ("خارج تخصصي"، "لا يتوفر وقت حاليًا"، "أخرى") + textarea. Buttons: danger outline "تأكيد الرفض", ghost "تراجع".
```

### Prompt 6 — Request detail, client view (after reply)

```
Design the same request detail screen as seen by the CLIENT (requester), after the accountant replied. Status pill "تم الرد" (teal-muted).

RIGHT column:
- "تفاصيل طلبك" card (same as before, read-only).
- "الرد" card: accountant avatar + name + verified badge + time "أمس ١٠:٣٠ م". Reply text in a white bubble with a hairline border, radius 16px (NOT WhatsApp colors): "أهلاً أستاذ أحمد، محتاج صورة الإخطار والإقرارات المقدمة عن ٢٠٢٢. أقترح مكالمة الثلاثاء الساعة ١٢ ظهرًا. التكلفة المبدئية ٣,٥٠٠ ج.م."
- Action row: matcha pill "قبول والمتابعة", ghost pill "رفض العرض", ghost pill "إغلاق الطلب".
- Timeline: أرسلت الطلب → قرأ المحاسب الطلب → رد المحاسب (latest = matcha node).

LEFT column:
- "المحاسب" card: avatar, name, headline, specialty chips, ghost "عرض الملف العام".
- "إلغاء الطلب" text link in danger color at the bottom, disabled with tooltip "لا يمكن الإلغاء بعد القبول" when the status is مقبول.
```

### Prompt 7 — My professional profile `/marketplace/profile` (accountant)

```
Design the accountant's "ملفي المهني" editor (sidebar item active).

Header: eyebrow "السوق المهني", title "ملفي المهني", description "هذا ما يراه العملاء في دليل المحاسبين على إي ضريبة." On the left: ghost pill "معاينة الملف العام" with an eye icon, and matcha pill "حفظ التغييرات".

Status banner (full width, radius 24px), shown as 3 variants stacked for the comp:
1. Pending: warning-tinted soft background, clock icon. "ملفك قيد المراجعة — يراجع فريق إي ضريبة بياناتك خلال يومي عمل قبل نشره."
2. Verified but not published: teal-wash background. "تم اعتماد ملفك ✓ — يمكنك نشره الآن ليظهر في الدليل." with a toggle switch "منشور في الدليل" (off).
3. Rejected: danger-tinted. "لم يتم اعتماد الملف — السبب: رقم القيد غير واضح. حدّث المؤهلات وأعد الإرسال." with a ghost button "إعادة الإرسال للمراجعة".

Body: two columns.

RIGHT (form, 8/12) — card sections:
1. "البيانات الأساسية":
   - Avatar uploader (circle 96px + "تغيير الصورة")
   - Segmented "نوع الملف": فرد / مكتب
   - Inputs: "الاسم المعروض *", "العنوان المهني المختصر *" (helper: "سطر واحد يظهر تحت اسمك، مثال: محاسب قانوني متخصص في الفحص الضريبي")
   - Grid: "المحافظة *" select, "المنطقة" input, "سنوات الخبرة *" number
   - "رابط الملف" read-only LTR "edariba.com/marketplace/accountants/mahmoud-elsherif" with a copy icon
2. "النبذة المهنية *": rich-text area (simple toolbar: bold, list), counter.
3. "التخصصات": tag input with chips (removable ×) and suggestions "فحص ضريبي"، "قيمة مضافة"، "مسك دفاتر"، "تأسيس شركات"، "فاتورة إلكترونية".
4. "المؤهلات والتراخيص": repeatable rows (title, issuer, year) such as "زمالة جمعية المحاسبين والمراجعين المصرية — ٢٠١٢", with an "+ إضافة مؤهل" ghost button and delete icons.
5. "دراسة حالة (اختياري)": title input + textarea.

LEFT (4/12, sticky) — "معاينة البطاقة" live preview of the public directory card exactly as visitors see it (avatar, name, verified badge, headline, location, years, 3 chips, 2-line bio, pill button "تواصل مع المحاسب"), plus a "اكتمال الملف ٧٠٪" progress bar (teal on teal-muted) with a checklist of missing items.
```

### Prompt 8 — My services `/marketplace/services` (accountant)

```
Design "خدماتي" (sidebar item active).

Header: eyebrow "السوق المهني", title "خدماتي", description "باقات بسعر ثابت تظهر في ملفك وفي دليل الخدمات." Matcha pill "+ خدمة جديدة".

Filter tabs: "الكل ٥"، "منشورة ٣"، "مسودة ١"، "موقوفة ١".

Service cards grid (3 columns desktop, cards radius 24px). Each card:
- Thumbnail 16:9 at the top, radius 16px
- Category chip
- Title
- Price in IBM Plex 700: "١,٨٠٠ ج.م" + unit "إجمالي" / "/ شهر" / "للجلسة"
- 2 feature lines with small tick chips
- Status pill: منشورة / مسودة / موقوفة
- Footer actions: ghost "تعديل", icon toggle "نشر/إيقاف", "⋯" menu (معاينة، حذف)
Use mixed card heights (no identical bento).

Sample services: "مراجعة الإقرار الضريبي قبل التقديم ١,٨٠٠ ج.م إجمالي"، "إصلاح الفواتير المرفوضة ٩٠٠ ج.م إجمالي"، "استشارة ٣٠ دقيقة ٤٥٠ ج.م للجلسة"، "مسك دفاتر شهري ٢,٥٠٠ ج.م / شهر" (مسودة)، "تأسيس شركة ذات مسؤولية محدودة" (موقوفة).

Also design the create/edit DRAWER (slides from the right, 560px, backdrop blur), title "خدمة جديدة":
- العنوان *
- التصنيف * select: مسك الدفاتر، الضرائب، القوائم المالية، تأسيس الشركات، دراسات الجدوى، الفاتورة الإلكترونية
- السعر * with suffix "ج.م" + segmented وحدة السعر: إجمالي / شهري / للجلسة
- صورة الخدمة * (dashed 1.5px dropzone, radius 16px, "اسحب الصورة هنا أو اختر ملفًا — PNG أو JPG حتى ٢ ميجا")
- الوصف * rich text
- المميزات (tag list)
- الشارات (tag list, e.g. "الأكثر طلبًا")
Sticky drawer footer: matcha "حفظ ونشر", teal "حفظ كمسودة", ghost "إلغاء". Show the inline error "الصورة مطلوبة قبل النشر" on the dropzone.

Empty state variant: "لم تضف أي خدمة بعد — العملاء يفضلون الباقات بسعر واضح." + matcha "أضف خدمتك الأولى".
```

### Prompt 9 — Submit proposal `/marketplace/projects/:slug/propose` (freelancer)

```
Design the "Submit a proposal" screen for a freelance accountant. Breadcrumb "السوق ← المشروعات ← تقديم عرض".

Left sticky summary card:
- Project title "تجهيز القوائم المالية لعام ٢٠٢٤ لشركة ناشئة"
- Chips: client type "شركة ناشئة", category "القوائم المالية"
- Budget "١٥,٠٠٠ – ٢٥,٠٠٠ ج.م"
- Deadline "١٥ ديسمبر ٢٠٢٦"
- Badge "الدفع بضمان المنصة" with a shield icon
- Required skills chips
- Ghost link "تفاصيل المشروع"

Right form card "عرضك":
- "قيمة العرض *" with suffix ج.م; helper showing the budget range; warning hint if outside the range
- "مدة التنفيذ (أيام)"
- "خطاب العرض *" rich text, placeholder "اشرح خبرتك المشابهة، خطة التنفيذ، وما تحتاجه من العميل…"
- "سيتم تقديم العرض باسم:" read-only mini-card of the user's own profile
- Info strip: "يمكنك سحب العرض قبل أن يقبله العميل. لا يمكنك تقديم أكثر من عرض نشط على نفس المشروع."
- Actions: matcha "تقديم العرض", ghost "إلغاء"

Also: a blocking state when the user has no verified profile. A card titled "تحتاج ملفًا مهنيًا معتمدًا لتقديم العروض" with matcha "أنشئ ملفك المهني".
```

### Prompt 10 — My proposals `/marketplace/proposals` + project owner review

```
Screen A, "عروضي" (freelancer): header (eyebrow "السوق المهني", title "عروضي"), tabs "النشطة ٣" / "المؤرشفة ٨". Table: المشروع، العميل، قيمة العرض، المدة، الحالة، تاريخ التقديم، action. Status pills:
- مُقدَّم = matcha
- في القائمة المختصرة = teal-muted with a star icon
- مقبول = success
- مرفوض = danger soft
- مسحوب = grey
Row menu: "عرض"، "سحب العرض" (danger).

Screen B, "العروض المستلمة" for the project owner, route /marketplace/projects/:id/proposals:
- Header shows the project title, status pill "منشور", "٦ عروض", and ghost "إغلاق المشروع".
- Proposal comparison cards in a vertical list. Each card: freelancer avatar + name + verified badge + years of experience; price in big IBM Plex numerals; duration; 3-line cover letter excerpt with "قراءة المزيد"; actions: ghost "إضافة للقائمة المختصرة" (star), matcha "قبول العرض", ghost-danger "رفض".
- Sort pills: "الأقل سعرًا"، "الأسرع تنفيذًا"، "الأحدث".
- Accept confirmation drawer: "قبول عرض أ. محمود الشريف بقيمة ١٨,٠٠٠ ج.م؟ سيتم إبلاغ باقي المتقدمين بإغلاق المشروع." with buttons "تأكيد القبول" / "تراجع".
```

### Prompt 11 — Notifications dropdown (header bell)

```
Design the open notifications dropdown from the header bell. White panel, radius 16px, 380px wide, soft shadow, anchored to the bell on the left side of the header.
- Header row: "الإشعارات", text link "تعليم الكل كمقروء".
- Tabs: "الكل"، "السوق"، "الفواتير".
- List items: a 36px circular icon chip (teal-muted with a teal outline icon), 2-line text, time on the next line in muted 12px; unread items have a matcha dot and a teal-wash background:
  • "طلب جديد من أحمد سمير — فحص ضريبي" منذ ساعتين
  • "رد أ. محمود الشريف على طلبك" أمس
  • "تم اعتماد ملفك المهني ✓" منذ ٣ أيام
  • "عرض جديد على مشروعك: تجهيز القوائم المالية" منذ ٤ أيام
  • (existing type) "تم قبول الفاتورة INV-١٠٢٣ من مصلحة الضرائب" منذ ٥ أيام
- Footer: ghost full-width "عرض كل الطلبات".
```

---

## B. Public site pieces (edariba.com/marketplace) — changed components only

### Prompt 12 — Accountant profile: request CTA card + sign-in gate

```
Update two components of the existing public accountant profile page on edariba.com (same brand system; the page has a deep-green hero and a white sticky sidebar on the left in RTL).

1) Replace the old demo inquiry form in the sidebar with a "Request card" (white, radius 24px, sticky):
   - Header: green dot + "اطلب مساعدة من أ. محمود الشريف"
   - 3 benefit rows with small outline icons: "رد خلال يوم عمل في المتوسط"، "بياناتك لا تُشارك إلا مع هذا المحاسب"، "تابع طلبك من حسابك على إي ضريبة"
   - Service select "اختر خدمة (اختياري)" listing his services with prices
   - Matcha full-width pill "أرسل طلبك" with an arrow icon
   - Under it, muted 13px: "سنطلب منك تسجيل الدخول أو إنشاء حساب مجاني لإرسال الطلب ومتابعته."
   - Small text link: "لديك حساب؟ سجّل الدخول"

2) Design the app sign-in screen in "contextual" mode (shown when a visitor clicks "أرسل طلبك" while logged out). Split layout:
   - RIGHT half: white sign-in form. Logo, title "سجّل الدخول لإكمال طلبك", email input (LTR), password input with show/hide, matcha pill "تسجيل الدخول", a divider "أو", white pill "المتابعة بحساب Google" with the Google glyph, and the link "ليس لديك حساب؟ أنشئ حسابًا مجانيًا".
   - LEFT half: inset deep-green panel (#203524, radius 40px, faint 52px hairline grid masked at the edges). Inside it a white "context card" showing what the visitor was doing: accountant avatar, name, verified badge, the selected service and price, and the line "بعد تسجيل الدخول سنعيدك مباشرة إلى نموذج الطلب." Below it, 3 matcha-dot bullets about eDariba.
   - Also show the signup variant of the same screen: fields الاسم الأول، اسم العائلة، البريد الإلكتروني، رقم الموبايل, matcha button "إنشاء حساب ومتابعة الطلب", and the note "سنرسل لك رابط تفعيل على بريدك، وبعد التفعيل نكمل طلبك من حيث توقفت."

Mobile follow-up: "Mobile 390px: the request card becomes a sticky bottom bar with the matcha button 'أرسل طلبك'; the sign-in context card moves above the form as a compact strip."
```

---

## Correction prompt (use if Stitch drifts)

```
Fix the following everywhere on this screen without changing the layout:
- Direction must be RTL with the sidebar on the right.
- Fonts must be only "IBM Plex Sans Arabic" (headings, numbers) and "Tajawal" (body, labels, buttons).
- Remove any gold, purple, blue or gradient accents; the only accent is matcha #D1F470 used as a fill, the brand green is #203524, the page background is #F8FAF4.
- All buttons are full pills. Cards are white, radius 24px, 1px #E1E2DE border.
- Replace emoji with thin outlined line icons.
- Use Arabic-Indic digits and "ج.م" after amounts.
- No colored stripe on the left or right edge of cards.
```
