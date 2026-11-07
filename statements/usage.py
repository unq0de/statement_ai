from django.utils import timezone


def get_current_month_window():
    current_time = timezone.localtime()
    month_start = current_time.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    if current_time.month == 12:
        next_month = month_start.replace(year=current_time.year + 1, month=1)
    else:
        next_month = month_start.replace(month=current_time.month + 1)
    return month_start, next_month