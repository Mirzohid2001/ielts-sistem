from django.contrib import admin

from ..models import SATResource, SATResourceProgress, SATResourceBookmark, SATResourceNote


@admin.register(SATResource)
class SATResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'has_video', 'has_pdf', 'order', 'is_active', 'created_at')
    list_filter = ('subject', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'youtube_url')
    ordering = ('subject', 'order', '-created_at')
    list_editable = ('order', 'is_active')

    fieldsets = (
        (None, {
            'fields': ('title', 'subject', 'description', 'order', 'is_active'),
        }),
        ("Video (ixtiyoriy)", {
            'fields': ('video_file', 'youtube_url'),
            'description': "Video fayl yoki YouTube URL dan bittasi (yoki ikkalasi) bo'lishi mumkin.",
        }),
        ("PDF (ixtiyoriy)", {
            'fields': ('pdf_file',),
        }),
    )

    @admin.display(boolean=True, description="Video")
    def has_video(self, obj):
        return bool(obj.video_file or obj.youtube_id)

    @admin.display(boolean=True, description="PDF")
    def has_pdf(self, obj):
        return bool(obj.pdf_file)


@admin.register(SATResourceProgress)
class SATResourceProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'watch_percentage', 'watched', 'last_accessed_at')
    list_filter = ('watched', 'resource__subject')
    search_fields = ('user__username', 'resource__title')
    autocomplete_fields = ('user', 'resource')
    ordering = ('-last_accessed_at',)


@admin.register(SATResourceBookmark)
class SATResourceBookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'timestamp', 'created_at')
    list_filter = ('resource__subject', 'created_at')
    search_fields = ('user__username', 'resource__title')
    autocomplete_fields = ('user', 'resource')
    ordering = ('-created_at',)


@admin.register(SATResourceNote)
class SATResourceNoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'short_note', 'timestamp', 'created_at')
    list_filter = ('resource__subject', 'created_at')
    search_fields = ('user__username', 'resource__title', 'note_text')
    autocomplete_fields = ('user', 'resource')
    ordering = ('-created_at',)

    @admin.display(description="Eslatma")
    def short_note(self, obj):
        txt = obj.note_text or ''
        return (txt[:60] + '...') if len(txt) > 60 else txt

