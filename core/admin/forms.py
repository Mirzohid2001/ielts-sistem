"""Admin: savol formasi, import/export resurslari (barcha savol turlari o'zgartirilmasdan)."""
import json

from django import forms
from import_export import resources

from ..models import Question, QuestionTypeRule, Test


def question_type_rules_json():
    """Savol turi bo'yicha shartlar — JS da tanlangan turda ko'rsatish uchun."""
    rules = QuestionTypeRule.objects.all().order_by('order', 'question_type')
    data = {r.question_type: (r.shart_text or '').strip() for r in rules}
    return json.dumps(data)


class TestResource(resources.ModelResource):
    class Meta:
        model = Test
        fields = (
            'id', 'title', 'category__name', 'test_type', 'difficulty', 'duration_minutes',
            'passing_score', 'allow_retake', 'max_attempts', 'is_active', 'created_at'
        )


class QuestionResource(resources.ModelResource):
    class Meta:
        model = Question
        fields = (
            'id', 'test__title', 'order', 'question_type', 'question_text',
            'correct_answer', 'points', 'created_at'
        )


class QuestionAdminForm(forms.ModelForm):
    """Savol turiga qarab admin validatsiya."""
    instruction_text = forms.CharField(
        required=False,
        label="Ko'rsatma (Instruction)",
        help_text="Masalan: ONE WORD ONLY yoki ONE WORD AND/OR A NUMBER (Listening uchun)",
    )
    instruction_box_style = forms.ChoiceField(
        required=False,
        label="Instruction banner uslubi",
        choices=[
            ("engnovate-red", "Engnovate (qizil/pushti quti)"),
            ("plain", "Plain (qutisiz oddiy matn)"),
            ("gray", "Gray (kulrang quti)"),
        ],
        help_text="Ko'rsatma matni (instruction_text) alohida banner quti bo'lib chiqishi uchun uslub.",
    )
    prompt_text_style = forms.ChoiceField(
        required=False,
        label="Question matn uslubi (headline/prompt)",
        choices=[
            ("default", "Default (hozirgi)"),
            ("headline", "Headline (katta/qalin)"),
            ("plain", "Plain (oddiy)"),
        ],
        help_text="Savol matni (question_text) headline/prompt sifatida ajralib turishi uchun uslub.",
    )
    fill_answers = forms.CharField(
        required=False,
        label="To'g'ri javoblar (vergul bilan)",
        help_text="Har bir bo'sh joy uchun to'g'ri javob; bo'sh joylar vergul bilan. Bitta yacheykada 2 ta so'z talab qilsangiz, ikkalasini bo'shliq bilan yozing — foydalanuvchi ikkalasini ham kiritishi kerak. Masalan: teacher,durability strength,skyscrapers",
    )
    matching_items = forms.CharField(
        required=False,
        label="Matching itemlar (savol bandlari)",
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': "1|Birinchisi matn...\n2|Ikkinchisi matn...\n3|Uchinchisi matn...\n4|To'rtinchisi matn...\n5|Beshinchisi matn...",
        }),
        help_text="Har satr: raqam|Matn (vergul | majburiy). Yoki raqam bo'shliq Matn — tizim tuzatadi.",
    )
    matching_options = forms.CharField(
        required=False,
        label="Matching variantlar (tanlash ro'yxati)",
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': "A|Yanira Pineda\nB|Susanna Tol\nC|Elizabeth English\nD|Raisa Chowdhury\nE|Greg Spotts",
        }),
        help_text=(
            "Matching Headings: har satr i|Sarlavha yoki ii|Matn (rim i–vii). "
            "Yoki i. Sarlavha matni (|siz). "
            "Matching Features/Info: A|Paragraph A kabi harflar."
        ),
    )
    matching_correct = forms.CharField(
        required=False,
        label="To'g'ri javob (har band)",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': "14:ii\n15:v\n16:i\n\nMatching Headings: rim (i, ii, vii). Boshqa matching: A, B, C.",
        }),
        help_text="Har satr: savol_raqami:variant. Matching Headings — rim: 14:ii. Features/Info — harf: 15:A.",
    )
    list_options_simple = forms.CharField(
        required=False,
        label="List options",
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Har satr: A|Option text",
    )
    list_correct_simple = forms.CharField(
        required=False,
        label="List to'g'ri javob",
        help_text="Masalan: A,C",
    )
    option_e = forms.CharField(
        required=False,
        max_length=500,
        label="Variant E",
        help_text="5–8 ta variant kerak bo'lsa shu qatorlarni to'ldiring (saytda a–h harflari bilan chiqadi).",
    )
    option_f = forms.CharField(required=False, max_length=500, label="Variant F")
    option_g = forms.CharField(required=False, max_length=500, label="Variant G")
    option_h = forms.CharField(required=False, max_length=500, label="Variant H")
    mcq_options_advanced = forms.CharField(
        required=False,
        label="MCQ variantlar (ro'yxat — ixtiyoriy)",
        widget=forms.Textarea(attrs={
            'rows': 8,
            'data-role': 'qt-mcq',
            'placeholder': (
                "Odatda E–H maydonlari yetarli. Bu yerni faqat 9+ variant yoki maxsus tartib uchun ishlating.\n"
                "Har satr: harf|matn\n"
                "a|Birinchi\nb|Ikkinchi\n…\ni|To'qqizinchi"
            ),
        }),
        help_text=(
            "Har satr: <strong>harf|matn</strong>. Kamida 2, ko'pi bilan 10 ta qator; harflar takrorlanmasin. "
            "Bu maydon to'ldirilganda u ustunlik qiladi; A–H va pastdagi qatorlar testda shu ro'yxat bo'yicha chiqadi."
        ),
    )
    part_number = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        label="Part raqami",
        help_text=(
            "Reading: 1–3 (savollar 1–13, 14–26, 27–40 bo'linishi). "
            "Listening: 1–4 ixtiyoriy — bo'sh qoldirsangiz ham tizim 10+10+10+10 bo'lib beradi; "
            "aniq boshqarmoqchi bo'lsangiz har 10 ta uchun 1,2,3,4 kiriting. Writing: 1 = Task 1, 2 = Task 2."
        ),
    )
    writing_task_images = forms.CharField(
        required=False,
        label="Writing Task 1 — qo‘shimcha rasmlar (URL)",
        widget=forms.Textarea(attrs={
            'rows': 5,
            'data-role': 'qt-fill',
            'data-qt-field': 'writing_task_images',
            'placeholder': (
                "Har qator — bitta rasm URL (https://...) yoki media ichidagi yo‘l.\n"
                "Masalan:\n"
                "https://example.com/chart1.png\n"
                "https://example.com/chart2.png"
            ),
        }),
        help_text=(
            "Faqat <strong>Essay (Writing)</strong> va odatda <strong>Task 1 (Part = 1)</strong>. "
            "Bitta rasm uchun «Rasm» maydonidan ham foydalanish mumkin; bu yerda carousel uchun bir nechta URL qo‘shasiz."
        ),
    )
    sa_prompt_lines = forms.CharField(
        required=False,
        label="Qisqa savollar (jadvalsiz)",
        widget=forms.Textarea(attrs={
            'rows': 8,
            'data-role': 'qt-sa-rows',
            'placeholder': (
                "Har qator — bitta savol. Oxirida || va so'z cheklovi (1, 2 yoki 3).\n"
                "What type of mineral were the Dolaucothi mines built to extract?||2\n"
                "Whose name might be carved onto a tunnel?||2"
            ),
        }),
        help_text=(
            "Faqat «Qisqa javob». Jadvalsiz IELTS uslubi. Bo'sh = [1] matn ichida. "
            "Format: savol matni||2 (ikki vertikal chiziq + 1 yoki 2 yoki 3)."
        ),
    )

    class Meta:
        model = Question
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'order' in self.fields:
            self.fields['order'].help_text = (
                "Test ichida ketma-ket tartib: 1, 2, 3, … Saytda shu tartibda ko'rinadi. "
                "Listening 40 savol: 1–10 Part 1, 11–20 Part 2, … (Part maydoni bo'sh bo'lsa ham tizim bo'lib beradi)."
            )
        if 'variant' in self.fields:
            self.fields['variant'].help_text = (
                "Agar testda «Variantlar soni = 2» bo'lsa — har bir savol uchun Variant 1 yoki 2 majburiy tanlang; "
                "aks holda barcha savollar bir variantda chiqadi."
            )
        # Savol turiga qarab JS maydonlarni yashirish uchun data-role (admin) — faqat MCQ/T-F/T-F NG/Y-N NG da ko'rinadi
        for fname in (
            'max_choices', 'option_a', 'option_b', 'option_c', 'option_d',
            'option_e', 'option_f', 'option_g', 'option_h', 'correct_answer',
        ):
            if fname in self.fields:
                self.fields[fname].widget.attrs.setdefault('data-role', 'qt-mcq')
        for fname in ('part_number', 'instruction_text', 'fill_answers', 'writing_task_images', 'matching_items', 'matching_options',
                      'matching_correct', 'list_options_simple', 'list_correct_simple'):
            if fname in self.fields:
                self.fields[fname].widget.attrs.setdefault('data-role', 'qt-fill')
                # JS uchun: qaysi maydonligini farqlash (granular show/hide)
                self.fields[fname].widget.attrs.setdefault('data-qt-field', fname)

        # Notes/Summary completion uchun format yo'riqnomasi
        fill_note_types = ('notes_completion', 'summary_completion', 'sentence_completion', 'table_completion')
        if self.instance and self.instance.question_type in fill_note_types:
            self.fields['question_text'].help_text = (
                "Matnda bo'sh joylar uchun [1], [2], [3] yozing. "
                "Misol: 'Accommodation: [1] Hotel on George Street. Cost: £ [2] (approx.)' "
                "Keyin 'To'g'ri javoblar' maydonida: central,85"
            )
        elif self.instance and self.instance.question_type == 'essay':
            self.fields['question_text'].help_text = (
                "To'liq task matni. Masalan: 'You should spend about 20 minutes...' va savol/diagram tavsifi."
            )
        elif self.instance and self.instance.question_type == 'short_answer':
            self.fields['question_text'].help_text = (
                "Jadvalsiz savollar: yuqoridagi «Qisqa savollar» maydonini to'ldiring. "
                "Yoki [1], [2] qavsli bitta matn. Sarlavha: Questions 11–13, Answer the questions below."
            )
        inst = self.instance
        opts = (inst.options_json or {}) if inst else {}
        # UI presetlar (instruction/banner va prompt uslubi)
        # Agar admin umuman tanlamasa, options_json ga yozilmasligi uchun default qiymat bermaymiz.
        self.fields['instruction_box_style'].initial = opts.get('ui_instruction_box_style')
        self.fields['prompt_text_style'].initial = opts.get('ui_prompt_text_style')
        corr = (inst.correct_answer_json if inst else None)

        self.fields['instruction_text'].initial = opts.get('instruction', '')
        img_list = opts.get('images') or []
        if isinstance(img_list, list) and img_list and 'writing_task_images' in self.fields:
            lines = []
            for it in img_list:
                if isinstance(it, str) and it.strip():
                    lines.append(it.strip())
                elif isinstance(it, dict):
                    u = (it.get('url') or it.get('path') or '').strip()
                    if u:
                        lines.append(u)
            self.fields['writing_task_images'].initial = '\n'.join(lines)
        if opts.get('part') is not None:
            try:
                self.fields['part_number'].initial = int(opts['part'])
            except (TypeError, ValueError):
                pass

        if inst and inst.question_type in ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer'):
            if isinstance(corr, list):
                self.fields['fill_answers'].initial = ', '.join(str(x) for x in corr)
            elif inst.correct_answer:
                self.fields['fill_answers'].initial = inst.correct_answer
            if inst.question_type == 'short_answer':
                sa = opts.get('short_answer_items') or []
                if isinstance(sa, list) and sa:
                    lines = []
                    for x in sa:
                        if not isinstance(x, dict):
                            continue
                        p = (x.get('prompt') or x.get('text') or '').strip()
                        mw = x.get('max_words')
                        if mw in (1, 2, 3):
                            lines.append(f"{p}||{mw}")
                        elif p:
                            lines.append(p)
                    self.fields['sa_prompt_lines'].initial = '\n'.join(lines)

        if inst and inst.question_type in ('matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification'):
            items = opts.get('items', [])
            if inst.question_type == 'matching_headings':
                headings = opts.get('headings', []) or opts.get('options', [])
            else:
                headings = opts.get('options', []) or opts.get('headings', [])
            if items:
                self.fields['matching_items'].initial = "\n".join(
                    f"{i.get('num', idx+1)}|{i.get('label', '')}" for idx, i in enumerate(items) if isinstance(i, dict)
                )
            if headings:
                self.fields['matching_options'].initial = "\n".join(
                    f"{h.get('letter', '')}|{h.get('text', '')}" for h in headings if isinstance(h, dict)
                )
            if isinstance(corr, dict):
                self.fields['matching_correct'].initial = "\n".join(f"{k}:{v}" for k, v in corr.items())

        if inst and inst.question_type == 'list_selection':
            options = opts.get('options', [])
            if options:
                self.fields['list_options_simple'].initial = "\n".join(
                    f"{o.get('letter', '')}|{o.get('text', '')}" for o in options if isinstance(o, dict)
                )
            if isinstance(corr, list):
                self.fields['list_correct_simple'].initial = ",".join(str(x) for x in corr)

        if inst and inst.question_type == 'mcq':
            mcq_opts = opts.get('options') or []
            if isinstance(mcq_opts, list) and mcq_opts:
                by_let = {}
                for o in mcq_opts:
                    if isinstance(o, dict) and o.get('letter'):
                        lt = str(o['letter']).strip().lower()
                        if lt:
                            by_let[lt] = (o.get('text') or '').strip()
                if by_let and all(k in 'abcdefgh' for k in by_let) and len(mcq_opts) <= 8:
                    for L in 'abcdefgh':
                        fname = f'option_{L}'
                        if fname in self.fields and L in by_let:
                            self.fields[fname].initial = by_let[L]
                else:
                    lines = []
                    for o in mcq_opts:
                        if isinstance(o, dict):
                            lines.append(f"{o.get('letter', '')}|{o.get('text', '')}".strip())
                    self.fields['mcq_options_advanced'].initial = "\n".join(lines)

        # To'g'ri javob maydoni — har doim qisqa yo'riqnoma
        self.fields['correct_answer'].help_text = (
            "MCQ: to'g'ri variant harfi (masalan: d yoki g). A–H yoki ro'yxatdagi harflardan biri. "
            "2 ta tanlov: a,c. True/False: a yoki b. T/F/NG va Y/N/NG: a, b yoki c."
        )

    def clean(self):
        cleaned = super().clean()
        q_type = cleaned.get('question_type')
        question_text = (cleaned.get('question_text') or '').strip()
        has_content = bool(question_text)  # Bo'sh savol = draft, qattiq validatsiya qo'llanmaydi
        correct_answer = (cleaned.get('correct_answer') or '').strip().lower()
        correct_json = cleaned.get('correct_answer_json')
        options_json = (
            dict(self.instance.options_json or {})
            if getattr(self.instance, 'pk', None)
            else dict(cleaned.get('options_json') or {})
        )
        sa_prompt_lines = (cleaned.get('sa_prompt_lines') or '').strip()
        instruction_text = (cleaned.get('instruction_text') or '').strip()
        instruction_box_style = cleaned.get('instruction_box_style')
        prompt_text_style = cleaned.get('prompt_text_style')
        part_number = cleaned.get('part_number')
        fill_answers = (cleaned.get('fill_answers') or '').strip()
        matching_items = (cleaned.get('matching_items') or '').strip()
        matching_options = (cleaned.get('matching_options') or '').strip()
        matching_correct = (cleaned.get('matching_correct') or '').strip()
        list_options_simple = (cleaned.get('list_options_simple') or '').strip()
        list_correct_simple = (cleaned.get('list_correct_simple') or '').strip()
        mcq_options_advanced = (cleaned.get('mcq_options_advanced') or '').strip()
        writing_task_images = (cleaned.get('writing_task_images') or '').strip()

        single_choice = ('mcq', 'true_false', 'true_false_not_given', 'yes_no_not_given')
        fill_types = ('fill_blank', 'summary_completion', 'notes_completion', 'sentence_completion', 'table_completion', 'short_answer')
        matching_types = ('matching_headings', 'matching_features', 'matching_info', 'matching_sentences', 'classification')

        mcq_allowed_letters = None
        if q_type == 'mcq':
            if mcq_options_advanced:
                parsed_mcq = []
                seen_let = set()
                for raw_line in mcq_options_advanced.splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '|' not in line:
                        raise forms.ValidationError(
                            "MCQ ro'yxatida har satrda «|» bo'lishi kerak: harf|matn. Masalan: a|Variant matni"
                        )
                    left, right = line.split('|', 1)
                    letter = left.strip().lower()
                    if not letter:
                        continue
                    letter = letter[0] if len(letter) > 1 and letter[0].isalpha() else letter
                    if not letter.isalpha() or len(letter) != 1:
                        raise forms.ValidationError(
                            f"Noto'g'ri harf: «{left.strip()}». Har bir qator boshida bitta lotin harfi (a–z)."
                        )
                    if letter in seen_let:
                        raise forms.ValidationError(f"Takrorlanuvchi harf: {letter}")
                    seen_let.add(letter)
                    parsed_mcq.append({'letter': letter, 'text': right.strip()})
                if len(parsed_mcq) < 2:
                    raise forms.ValidationError("MCQ ro'yxatida kamida 2 ta variant (2 qator) bo'lishi kerak.")
                if len(parsed_mcq) > 10:
                    raise forms.ValidationError("MCQ da ko'pi bilan 10 ta variant.")
                options_json['options'] = parsed_mcq
                mcq_allowed_letters = tuple(o['letter'] for o in parsed_mcq)
            else:
                field_map = [
                    ('a', cleaned.get('option_a')),
                    ('b', cleaned.get('option_b')),
                    ('c', cleaned.get('option_c')),
                    ('d', cleaned.get('option_d')),
                    ('e', cleaned.get('option_e')),
                    ('f', cleaned.get('option_f')),
                    ('g', cleaned.get('option_g')),
                    ('h', cleaned.get('option_h')),
                ]
                parsed_from_fields = []
                for letter, val in field_map:
                    t = (val or '').strip()
                    if t:
                        parsed_from_fields.append({'letter': letter, 'text': t})
                if has_content and len(parsed_from_fields) == 1:
                    raise forms.ValidationError("MCQ: kamida 2 ta variant (A–H) kiriting.")
                letters_in_parsed = [o['letter'] for o in parsed_from_fields]
                needs_json_list = len(parsed_from_fields) > 4 or any(x in 'efgh' for x in letters_in_parsed)
                if len(parsed_from_fields) >= 2:
                    if needs_json_list:
                        options_json['options'] = parsed_from_fields
                        mcq_allowed_letters = tuple(letters_in_parsed)
                    else:
                        options_json.pop('options', None)
                else:
                    options_json.pop('options', None)

        # MCQ/True-False da 2 ta javob: correct_answer "a,c" -> correct_answer_json ["a","c"]
        max_choices = cleaned.get('max_choices') or 1
        if q_type in single_choice and max_choices == 2 and correct_answer:
            if q_type == 'mcq':
                allowed_for_dual = set(mcq_allowed_letters) if mcq_allowed_letters else {'a', 'b', 'c', 'd'}
            elif q_type == 'true_false':
                allowed_for_dual = {'a', 'b'}
            else:
                allowed_for_dual = {'a', 'b', 'c'}
            parts = [
                x.strip().lower()
                for x in correct_answer.replace(',', ' ').split()
                if x.strip() and x.strip().lower() in allowed_for_dual
            ]
            if len(parts) >= 2:
                cleaned['correct_answer_json'] = sorted(set(parts))[:2]
                cleaned['correct_answer'] = cleaned['correct_answer_json'][0]
                correct_answer = cleaned['correct_answer']
            elif len(parts) == 1:
                raise forms.ValidationError(
                    "«Tanlash soni» 2 ta javob qilib tanlangan. «To'g'ri javob» da ikkita harf kiriting (masalan: a,c)."
                )

        if instruction_text:
            options_json['instruction'] = instruction_text
        # Admin UI presetlarni options_json ichiga yozamiz (render paytida o'qiladi)
        if instruction_box_style:
            options_json['ui_instruction_box_style'] = instruction_box_style
        if prompt_text_style:
            options_json['ui_prompt_text_style'] = prompt_text_style
        if part_number is not None and part_number >= 1:
            options_json['part'] = part_number

        if q_type == 'essay':
            if writing_task_images:
                urls = [
                    ln.strip()
                    for ln in writing_task_images.splitlines()
                    if ln.strip() and not ln.strip().startswith('#')
                ]
                if urls:
                    options_json['images'] = urls
            elif getattr(self.instance, 'pk', None):
                # Yangi savolda bo'sh textarea JSON dagi images ni saqlab qoladi
                options_json.pop('images', None)

        if q_type in fill_types and fill_answers:
            parsed = [x.strip() for x in fill_answers.replace('\n', ',').split(',') if x.strip()]
            if parsed:
                cleaned['correct_answer_json'] = parsed
                options_json['blanks_count'] = len(parsed)
                correct_json = parsed

        if q_type == 'short_answer' and sa_prompt_lines:
            sa_items = []
            for raw in sa_prompt_lines.splitlines():
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                mw = None
                prompt = line
                if '||' in line:
                    prompt, _, rest = line.rpartition('||')
                    prompt = prompt.strip()
                    rs = rest.strip()
                    if rs.isdigit():
                        mw = int(rs)
                if mw is not None and mw not in (1, 2, 3):
                    raise forms.ValidationError(
                        f"«{line[:60]}…»: so'z cheklovi faqat 1, 2 yoki 3 bo'lishi kerak (|| dan keyin)."
                    )
                if not prompt:
                    raise forms.ValidationError("Har qatorida savol matni bo'lishi kerak (|| dan oldin).")
                sa_items.append({'prompt': prompt, 'max_words': mw})
            if sa_items:
                if has_content:
                    if not correct_json or not isinstance(correct_json, list):
                        raise forms.ValidationError(
                            "Jadvalsiz qisqa savollar: «To'g'ri javoblar» da har savol uchun bitta javob, vergul bilan — "
                            f"{len(sa_items)} ta javob kiriting."
                        )
                    if len(correct_json) != len(sa_items):
                        raise forms.ValidationError(
                            f"Savollar soni ({len(sa_items)}) va to'g'ri javoblar soni ({len(correct_json)}) mos kelmaydi."
                        )
                options_json['short_answer_items'] = sa_items
        elif q_type != 'short_answer':
            options_json.pop('short_answer_items', None)
        elif q_type == 'short_answer' and not sa_prompt_lines:
            options_json.pop('short_answer_items', None)

        if q_type in matching_types and (matching_items or matching_options or matching_correct):
            import re
            items = []
            for idx, line in enumerate([ln.strip() for ln in matching_items.splitlines() if ln.strip()]):
                if '|' in line:
                    left, right = line.split('|', 1)
                    left, right = left.strip(), right.strip()
                    num = int(left) if left.isdigit() else (idx + 1)
                    items.append({'num': num, 'label': right})
                else:
                    # Vergulsiz: "4 The fact..." yoki "41 The fact" (41 = 4| xato) -> raqam + matn
                    m = re.match(r'^(\d+)\s+(.+)$', line)
                    if m:
                        num = int(m.group(1))
                        if num >= 20:  # 41 -> 4, 51 -> 5 (vergul unutilganda)
                            num = int(str(num)[0])
                        label = m.group(2).strip()
                        items.append({'num': num, 'label': label})
                    else:
                        items.append({'num': idx + 1, 'label': line})

            headings = []
            for line in [ln.strip() for ln in matching_options.splitlines() if ln.strip()]:
                if '|' in line:
                    letter, text = line.split('|', 1)
                    lt = letter.strip().lower()
                    headings.append({'letter': lt, 'text': text.strip()})
                else:
                    mrom = re.match(r'^([ivxlcdm]+)\s*[.):\-]?\s*(.*)$', line, re.I)
                    if mrom and mrom.group(1):
                        tx = (mrom.group(2) or '').strip()
                        headings.append({'letter': mrom.group(1).lower(), 'text': tx})
                    else:
                        parts = line.split(None, 1)
                        tok = parts[0] if parts else ''
                        if len(tok) == 1 and tok.isalpha():
                            headings.append({'letter': tok.lower(), 'text': (parts[1] if len(parts) > 1 else '').strip()})

            corr_map = {}
            for line in [ln.strip() for ln in matching_correct.splitlines() if ln.strip()]:
                if ':' in line:
                    k, v = line.split(':', 1)
                    corr_map[k.strip()] = v.strip().lower()
                else:
                    m = re.match(r'^(\d+)\s+(.+)$', line)
                    if m:
                        corr_map[m.group(1).strip()] = m.group(2).strip().lower()

            if items:
                options_json['items'] = items
            if headings:
                options_json['headings'] = headings
            if corr_map:
                cleaned['correct_answer_json'] = corr_map
                correct_json = corr_map

            if has_content:
                if q_type in matching_types and (not items or not corr_map):
                    raise forms.ValidationError(
                        "Matching: «Matching itemlar» (masalan 14|Paragraph A) va «To'g'ri javob» (14:ii yoki 14: ii) majburiy."
                    )
                if q_type == 'matching_headings' and not headings:
                    raise forms.ValidationError(
                        "Matching Headings: «Matching variantlar» da sarlavhalar ro'yxati — har satr: i|Tried and tested yoki ii|Cooperation..."
                    )

        if q_type == 'list_selection' and (list_options_simple or list_correct_simple):
            options = []
            for line in [ln.strip() for ln in list_options_simple.splitlines() if ln.strip()]:
                if '|' in line:
                    letter, text = line.split('|', 1)
                    options.append({'letter': letter.strip(), 'text': text.strip()})
                else:
                    options.append({'letter': line[:1].upper(), 'text': line})

            corr_list = [x.strip() for x in list_correct_simple.replace(' ', '').split(',') if x.strip()]
            if options:
                options_json['options'] = options
            if corr_list:
                cleaned['correct_answer_json'] = corr_list
                correct_json = corr_list

        cleaned['options_json'] = options_json

        # Savol matni bo'sh bo'lsa (draft) — to'g'ri javob / fill / matching majburiy emas; klient keyinroq to'ldiradi
        if has_content:
            if q_type in single_choice:
                if q_type == 'mcq' and max_choices == 2:
                    pass
                elif not correct_answer:
                    raise forms.ValidationError(
                        "«To'g'ri javob» majburiy (bitta harf yoki 2 ta tanlovda vergul bilan ikkita harf)."
                    )
                elif q_type == 'mcq':
                    allowed_mcq = set(mcq_allowed_letters or ('a', 'b', 'c', 'd'))
                    if correct_answer not in allowed_mcq:
                        raise forms.ValidationError(
                            "«To'g'ri javob» faqat mavjud variantlardan biri bo'lishi kerak: "
                            + ", ".join(sorted(allowed_mcq)) + "."
                        )
                else:
                    allowed_tf = {
                        'true_false': {'a', 'b'},
                        'true_false_not_given': {'a', 'b', 'c'},
                        'yes_no_not_given': {'a', 'b', 'c'},
                    }.get(q_type, set())
                    if correct_answer not in allowed_tf:
                        raise forms.ValidationError(
                            "«To'g'ri javob» faqat: " + ", ".join(sorted(allowed_tf)) + "."
                        )

            if q_type in fill_types:
                if not correct_json and not correct_answer:
                    raise forms.ValidationError(
                        "Bo'sh joy to'ldirish turlarida «To'g'ri javoblar (vergul bilan)» maydonini to'ldiring. Masalan: javob1,javob2,javob3"
                    )
                if correct_json and not isinstance(correct_json, list):
                    raise forms.ValidationError("To'g'ri javoblar ro'yxat ko'rinishida bo'lishi kerak (vergul bilan ajratilgan).")

            if q_type in matching_types:
                if not isinstance(correct_json, dict) or not correct_json:
                    raise forms.ValidationError(
                        "Matching turlarida «Matching to'g'ri javob» maydonini to'ldiring. Har satrda: 1:A, 2:B formatida."
                    )

            if q_type == 'list_selection':
                if not isinstance(correct_json, list) or not correct_json:
                    raise forms.ValidationError("List selection da «List to'g'ri javob» maydonini to'ldiring. Masalan: A,C")

        return cleaned

    def save(self, commit=True):
        """options_json va correct_answer_json inline da render bo'lmasa ham aniq saqlansin."""
        instance = super().save(commit=False)
        if 'options_json' in self.cleaned_data:
            instance.options_json = self.cleaned_data['options_json']
        if 'correct_answer_json' in self.cleaned_data:
            instance.correct_answer_json = self.cleaned_data['correct_answer_json']
        if commit:
            instance.save()
        return instance
