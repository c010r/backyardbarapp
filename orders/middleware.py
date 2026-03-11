class SubdomainMiddleware:
    """
    Selecciona el URL conf según el subdominio:
      - pedidos.*  →  backyardbar.urls_orders
      - todo lo demás  →  ROOT_URLCONF (menú)
    """
    ORDERS_URLCONF = 'backyardbar.urls_orders'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        if host.startswith('pedidos.') or host == 'pedidos':
            request.urlconf = self.ORDERS_URLCONF
        return self.get_response(request)
