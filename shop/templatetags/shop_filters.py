from django import template

# 템플릿 태그 라이브러리 등록
register = template.Library()

@register.filter
def multiply(value, arg):
    """
    두 숫자를 곱하는 템플릿 필터

    사용 예: {{ price|multiply:quantity }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
