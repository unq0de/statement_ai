from django.contrib import admin

from .models import APIUsageRecord, AuditEvent, GeminiUsageRecord


@admin.register(APIUsageRecord)
class APIUsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'user',
        'method',
        'endpoint',
        'status_code',
        'duration_ms',
        'request_size_bytes',
    )
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('user__username', 'user__email', 'endpoint')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'user',
        'endpoint',
        'method',
        'status_code',
        'duration_ms',
        'request_size_bytes',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(GeminiUsageRecord)
class GeminiUsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'user',
        'statement',
        'model_name',
        'status',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
        'duration_ms',
        'error_type',
    )
    list_filter = ('model_name', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'model_name')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'user',
        'statement',
        'model_name',
        'status',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
        'duration_ms',
        'error_type',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'event_type',
        'outcome',
        'actor',
        'target_type',
        'target_id',
        'request_route',
    )
    list_filter = ('event_type', 'outcome', 'created_at')
    search_fields = ('actor__username', 'event_type', 'target_type', 'target_id')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'actor',
        'event_type',
        'outcome',
        'target_type',
        'target_id',
        'request_method',
        'request_route',
        'details',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
