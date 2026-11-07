from .models import AuditEvent


def record_audit_event(
    event_type,
    *,
    request=None,
    actor=None,
    target_type='',
    target_id='',
    outcome='success',
    details=None,
):
    source_request = getattr(request, '_request', request)
    if actor is None and source_request is not None:
        request_user = getattr(source_request, 'user', None)
        if getattr(request_user, 'is_authenticated', False):
            actor = request_user

    resolver_match = getattr(source_request, 'resolver_match', None)
    route = getattr(resolver_match, 'route', '') or ''
    if not route and source_request is not None:
        route = getattr(source_request, 'path_info', '').lstrip('/')

    return AuditEvent.objects.create(
        actor=actor,
        event_type=event_type,
        outcome=outcome,
        target_type=target_type,
        target_id=str(target_id) if target_id else '',
        request_method=getattr(source_request, 'method', '')[:10],
        request_route=route[:255],
        details=details or {},
    )
