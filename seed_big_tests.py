"""
Standalone seed runner.

Foydalanish:
  1) requirements'ni o‘rnating (agar hali o‘rnatilmagan bo‘lsa):
       python3 -m pip install -r requirements.txt
  2) Skriptni ishga tushiring:
       python3 seed_big_tests.py reset_and_seed

Mode'lar:
  - reset_and_seed
      Bazani tozalaydi va seed_new_format uslubidagi ideal katta testlar qo‘shadi,
      keyin testlar sonini oshirish uchun nusxa (clone) qiladi.
      Default target: Reading=6, Listening=6, Writing=6.
  - seed_new_format
      Bazani tozalamasdan seed_new_format-ni ishga tushiradi (agar komanda ichida tozalash bo‘lsa, shunga qarab).
  - load_new_format_tests
      load_new_format_tests komandasini ishga tushiradi; --wipe argumentini qo‘llab yuboradi (ixtiyoriy).
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    # Cursor/terminal qaysi joyda ekanidan qat'iy nazar settings topilsin.
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(workspace_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django  # noqa: E402

    django.setup()

    from django.core.management import call_command  # noqa: E402

    mode = sys.argv[1] if len(sys.argv) >= 2 else "reset_and_seed"
    extra = sys.argv[2:]

    def get_int_flag(flag_name: str, default: int) -> int:
        flag = f"--{flag_name}"
        if flag in extra:
            idx = extra.index(flag)
            if idx + 1 < len(extra):
                try:
                    return int(extra[idx + 1])
                except ValueError:
                    return default
        return default

    if mode == "reset_and_seed":
        # Command: python manage.py reset_and_seed
        call_command("reset_and_seed", **({"no_seed": False} if "no_seed" in extra else {}))

        # Clone yordamida testlar sonini oshirish
        from core.models import Category, Test, ReadingPassage, Question  # noqa: E402
        import copy  # noqa: E402

        target_reading = get_int_flag("reading", 6)
        target_listening = get_int_flag("listening", 6)
        target_writing = get_int_flag("writing", 6)

        # Category slug'lar test_type bilan bir xil (reading/listening/writing)
        targets = {
            "reading": target_reading,
            "listening": target_listening,
            "writing": target_writing,
        }

        def clone_test_set(test_type: str, target_count: int) -> None:
            cat = Category.objects.filter(slug=test_type).first()
            if not cat:
                return
            # "Namuna:" (savol turlari bo'yicha coverage) testlarini big clone maqsadiga kiritmaymiz.
            base_qs = (
                Test.objects.filter(category=cat, test_type=test_type)
                .exclude(title__startswith="Namuna:")
                .order_by("created_at")
            )
            existing = base_qs.count()
            if existing >= target_count:
                return
            base = base_qs.first()
            if not base:
                return

            # Clone uchun template questions/passages
            base_passages = list(base.reading_passages.all().order_by("order"))
            base_questions = list(base.questions.all().order_by("order", "id"))

            # Test va savollarni nusxalash (id/created_at/updated_at tashlanadi)
            def _test_field_data(t: Test, title_override: str):
                data = {}
                for f in t._meta.fields:
                    if f.name in ("id", "created_at", "updated_at"):
                        continue
                    # title alohida beriladi
                    if f.name == "title":
                        continue
                    val = getattr(t, f.name)
                    # FileField/ImageField'lar deep copy qilinmaydi (FieldFile), faqat path/name
                    if f.get_internal_type() in ("FileField", "ImageField"):
                        data[f.name] = getattr(val, "name", "") if val else ""
                    else:
                        data[f.name] = copy.deepcopy(val)
                data["title"] = title_override
                return data

            def _question_field_data(q: Question):
                data = {}
                for f in q._meta.fields:
                    if f.name in ("id", "created_at", "test"):
                        continue
                    val = getattr(q, f.name)
                    if f.get_internal_type() in ("FileField", "ImageField"):
                        data[f.name] = getattr(val, "name", "") if val else ""
                    else:
                        data[f.name] = copy.deepcopy(val)
                return data

            clones_needed = target_count - existing
            start_idx = existing + 1
            for k in range(clones_needed):
                clone_idx = start_idx + k
                new_test_title = f"{base.title} (Clone {clone_idx})"
                new_test = Test.objects.create(**_test_field_data(base, new_test_title))

                # Reading passages
                if test_type == "reading":
                    for p in base_passages:
                        ReadingPassage.objects.create(
                            test=new_test,
                            order=p.order,
                            title=p.title,
                            text=p.text,
                            variant=p.variant,
                        )

                # Questions
                bulk_questions = []
                for q in base_questions:
                    qdata = _question_field_data(q)
                    qdata["test"] = new_test
                    bulk_questions.append(Question(**qdata))
                Question.objects.bulk_create(bulk_questions)

        clone_test_set("reading", target_reading)
        clone_test_set("listening", target_listening)
        clone_test_set("writing", target_writing)

        return 0

    if mode == "seed_new_format":
        # Command: python manage.py seed_new_format
        # --wipe opcioni seed_new_format ichida mavjud emas (seed_new_format.py parserda --wipe bor edi).
        # Agar kerak bo‘lsa, user: python3 seed_big_tests.py seed_new_format --wipe
        kwargs = {}
        if "--wipe" in extra:
            kwargs["wipe"] = True
        call_command("seed_new_format", **kwargs)
        return 0

    if mode == "load_new_format_tests":
        # Command: python manage.py load_new_format_tests [--wipe]
        kwargs = {}
        if "--wipe" in extra:
            kwargs["wipe"] = True
        call_command("load_new_format_tests", **kwargs)
        return 0

    print(f"Unknown mode: {mode}")
    print("Allowed modes: reset_and_seed, seed_new_format, load_new_format_tests")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

