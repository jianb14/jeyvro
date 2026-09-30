from django.contrib import admin

from .models import ContentFlag


@admin.register(ContentFlag)
class ContentFlagAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'kind', 'status', 'author', 'rules', 'rule_detail', 'created_at',
    )
    list_filter = ('kind', 'status')
    search_fields = ('author__email', 'rule_detail')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
