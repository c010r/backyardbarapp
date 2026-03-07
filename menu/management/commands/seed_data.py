from django.core.management.base import BaseCommand
from menu.models import Category, MenuItem, Table, SiteConfig


class Command(BaseCommand):
    help = 'Carga datos de ejemplo para Backyard Bar'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creando configuración...')
        config, _ = SiteConfig.objects.get_or_create(pk=1)
        config.bar_name = 'Backyard Bar'
        config.tagline = 'Good vibes & great drinks'
        config.footer_text = 'Backyard Bar • Buenos Aires • Buena vibra, siempre'
        config.primary_color = '#f5a623'
        config.secondary_color = '#1a1a2e'
        config.save()

        self.stdout.write('Creando categorías...')
        categories = [
            {'name': 'Cervezas', 'icon': '🍺', 'description': 'Artesanales y de lata, frías como tienen que estar.', 'order': 1},
            {'name': 'Cócteles', 'icon': '🍹', 'description': 'Creaciones del bartender.', 'order': 2},
            {'name': 'Shots', 'icon': '🥃', 'description': 'Para los valientes.', 'order': 3},
            {'name': 'Sin alcohol', 'icon': '🧃', 'description': 'Para manejar o simplemente disfrutar.', 'order': 4},
            {'name': 'Para picar', 'icon': '🍟', 'description': 'Para no llegar con el estómago vacío.', 'order': 5},
        ]
        cat_objs = {}
        for c in categories:
            obj, _ = Category.objects.get_or_create(name=c['name'], defaults=c)
            cat_objs[c['name']] = obj

        self.stdout.write('Creando items del menú...')
        items = [
            # Cervezas
            {'category': 'Cervezas', 'name': 'Backyard Rubia', 'description': 'Nuestra lager artesanal, suave y refrescante. 500ml.', 'price': 1200, 'is_featured': True, 'order': 1},
            {'category': 'Cervezas', 'name': 'Backyard IPA', 'description': 'India Pale Ale con notas cítricas y amargor pronunciado. 500ml.', 'price': 1400, 'is_featured': True, 'order': 2},
            {'category': 'Cervezas', 'name': 'Backyard Stout', 'description': 'Negra con notas de café y chocolate. 500ml.', 'price': 1400, 'order': 3},
            {'category': 'Cervezas', 'name': 'Cerveza en lata', 'description': 'Selección del día. Preguntar al mozo.', 'price': 900, 'order': 4},
            # Cócteles
            {'category': 'Cócteles', 'name': 'Backyard Spritz', 'description': 'Aperol, prosecco, soda y naranja. Refrescante y veraniego.', 'price': 2200, 'is_featured': True, 'order': 1, 'tags': 'sin gluten'},
            {'category': 'Cócteles', 'name': 'Gin Tonic de la casa', 'description': 'Gin premium con tónica artesanal y botanicals de temporada.', 'price': 2500, 'order': 2},
            {'category': 'Cócteles', 'name': 'Mojito', 'description': 'Ron blanco, menta fresca, lima, azúcar y soda.', 'price': 2200, 'order': 3},
            {'category': 'Cócteles', 'name': 'Negroni', 'description': 'Gin, Campari y vermut rojo. Clásico inoxidable.', 'price': 2800, 'order': 4},
            {'category': 'Cócteles', 'name': 'Margarita', 'description': 'Tequila, triple sec, jugo de lima y sal en el borde.', 'price': 2400, 'order': 5},
            # Shots
            {'category': 'Shots', 'name': 'Tequila', 'description': 'Con sal y limón.', 'price': 1000, 'order': 1},
            {'category': 'Shots', 'name': 'Fernet con coca', 'description': 'El clásico argentino. Porción generosa.', 'price': 1200, 'order': 2, 'is_featured': True},
            {'category': 'Shots', 'name': 'Jager Bomb', 'description': 'Jägermeister + Red Bull.', 'price': 1800, 'order': 3},
            # Sin alcohol
            {'category': 'Sin alcohol', 'name': 'Limonada de la casa', 'description': 'Limón, menta y azúcar mascabo. Bien fría.', 'price': 900, 'order': 1, 'tags': 'vegano,sin gluten'},
            {'category': 'Sin alcohol', 'name': 'Virgin Mojito', 'description': 'Igual que el mojito pero sin alcohol. Igual de rico.', 'price': 1200, 'order': 2, 'tags': 'vegano'},
            {'category': 'Sin alcohol', 'name': 'Agua mineral', 'description': 'Con o sin gas.', 'price': 500, 'order': 3},
            {'category': 'Sin alcohol', 'name': 'Gaseosa', 'description': 'Coca, Sprite o agua tónica.', 'price': 700, 'order': 4},
            # Para picar
            {'category': 'Para picar', 'name': 'Papas fritas', 'description': 'Con mayo o ketchup. Crocantes y bien cargadas.', 'price': 1400, 'order': 1, 'tags': 'vegano'},
            {'category': 'Para picar', 'name': 'Tabla de quesos', 'description': 'Selección de quesos, frutos secos y tostadas.', 'price': 2800, 'is_featured': True, 'order': 2},
            {'category': 'Para picar', 'name': 'Empanadas (x4)', 'description': 'Dos de carne y dos de jamón y queso. Del horno.', 'price': 2000, 'order': 3},
            {'category': 'Para picar', 'name': 'Nachos', 'description': 'Con guacamole, salsa roja y crema ácida.', 'price': 1800, 'order': 4, 'tags': 'vegano'},
        ]
        for item_data in items:
            cat_name = item_data.pop('category')
            item_data['category'] = cat_objs[cat_name]
            MenuItem.objects.get_or_create(
                name=item_data['name'],
                category=item_data['category'],
                defaults=item_data
            )

        self.stdout.write('Creando mesas...')
        for i in range(1, 11):
            Table.objects.get_or_create(number=i)
        # Mesas especiales
        Table.objects.get_or_create(number=20, defaults={'name': 'Terraza'})
        Table.objects.get_or_create(number=21, defaults={'name': 'Barra'})
        Table.objects.get_or_create(number=22, defaults={'name': 'VIP'})

        self.stdout.write(self.style.SUCCESS('Datos de ejemplo creados exitosamente!'))
        self.stdout.write(self.style.WARNING(
            '\nProximo paso: generá los QR desde http://localhost:8000/admin-tools/qr-dashboard/'
        ))
