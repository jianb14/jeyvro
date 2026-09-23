"""API response conventions (PROJECT_CONTEXT §8, data-layer contract).

Every list endpoint returns the {count, items} envelope — never one-off
shapes. Wired globally via REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CountItemsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'items': data,
        })
