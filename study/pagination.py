# pyrefly: ignore [missing-import]
from rest_framework.pagination import PageNumberPagination
# pyrefly: ignore [missing-import]
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        total_pages = self.page.paginator.num_pages if self.page else 1
        current_page = self.page.number if self.page else 1
        page_size = self.get_page_size(self.request) or self.page_size
        total = self.page.paginator.count if self.page else len(data)

        return Response({
            'success': True,
            'message': 'Data fetched successfully',
            'data': data,
            'pagination': {
                'page': current_page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages
            }
        })
