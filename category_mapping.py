"""
Category Mapping: Revolico -> Rico-Cuba
Mappt Revolico Kategorien auf Rico-Cuba Kategorien
"""

# Kategorie-Mapping basierend auf Keywords und Patterns
CATEGORY_MAPPINGS = {
    # Comprar & Vender (Shopping)
    'movil': 'Móviles',
    'telefono': 'Móviles',
    'smartphone': 'Móviles',
    'celular': 'Móviles',

    'foto': 'Foto / Video',
    'camara': 'Foto / Video',
    'video': 'Foto / Video',

    'tv': 'TV / Accesorios',
    'television': 'TV / Accesorios',

    'computadora': 'Computadoras',
    'laptop': 'Computadoras',
    'pc': 'Computadoras',
    'ordenador': 'Computadoras',

    'electrodomestico': 'Electrodomésticos',
    'nevera': 'Electrodomésticos',
    'refrigerador': 'Electrodomésticos',
    'lavadora': 'Electrodomésticos',
    'cocina': 'Electrodomésticos',
    'microondas': 'Electrodomésticos',
    'ventilador': 'Electrodomésticos',
    'plancha': 'Electrodomésticos',

    'mueble': 'Muebles y Decoración',
    'decoracion': 'Muebles y Decoración',
    'sofa': 'Muebles y Decoración',
    'cama': 'Muebles y Decoración',
    'mesa': 'Muebles y Decoración',
    'silla': 'Muebles y Decoración',

    'ropa': 'Ropa / Zapatos / Accesorios',
    'zapato': 'Ropa / Zapatos / Accesorios',
    'calzado': 'Ropa / Zapatos / Accesorios',
    'vestido': 'Ropa / Zapatos / Accesorios',
    'camisa': 'Ropa / Zapatos / Accesorios',
    'pantalon': 'Ropa / Zapatos / Accesorios',

    'mascota': 'Mascotas / Animales',
    'perro': 'Mascotas / Animales',
    'gato': 'Mascotas / Animales',
    'animal': 'Mascotas / Animales',

    'libro': 'Libros & Revistas',
    'revista': 'Libros & Revistas',

    'joya': 'Joyas / Relojes',
    'reloj': 'Joyas / Relojes',
    'anillo': 'Joyas / Relojes',

    'deporte': 'Equipamiento Deportivo',
    'bicicleta': 'Bicicletas',
    'bici': 'Bicicletas',

    # Vehículos
    'auto': 'Autos / Camiones / Remolques',
    'carro': 'Autos / Camiones / Remolques',
    'vehiculo': 'Autos / Camiones / Remolques',
    'camion': 'Autos / Camiones / Remolques',

    'moto': 'Motocicletas & Triciclos',
    'motocicleta': 'Motocicletas & Triciclos',

    'mecanico': 'Mecánico',
    'pieza': 'Piezas & Accesorios',
    'repuesto': 'Piezas & Accesorios',

    'taxi': 'Taxi & Servicio de Mensajería',
    'mensajeria': 'Taxi & Servicio de Mensajería',

    # Inmobiliaria
    'casa': 'Ofertas & Búsquedas',
    'apartamento': 'Ofertas & Búsquedas',
    'vivienda': 'Ofertas & Búsquedas',
    'inmueble': 'Ofertas & Búsquedas',

    'alquiler': 'Alquiler a Cubanos',
    'renta': 'Alquiler a Cubanos',

    'playa': 'Casa en la Playa',

    # Energía
    'solar': 'Paneles Solares / Accesorios',
    'panel': 'Paneles Solares / Accesorios',

    'generador': 'Generadores & Accesorios',
    'planta': 'Generadores & Accesorios',

    # Servicios
    'construccion': 'Trabajos de Construcción / Renovación / Mantenimiento',
    'renovacion': 'Trabajos de Construcción / Renovación / Mantenimiento',
    'mantenimiento': 'Trabajos de Construcción / Renovación / Mantenimiento',
    'albanil': 'Trabajos de Construcción / Renovación / Mantenimiento',
    'pintura': 'Trabajos de Construcción / Renovación / Mantenimiento',

    'programacion': 'IT / Programación',
    'informatica': 'IT / Programación',
    'software': 'IT / Programación',

    'reparacion': 'Reparaciones Electrónicas',
    'repara': 'Reparaciones Electrónicas',

    'curso': 'Cursos & Clases',
    'clase': 'Cursos & Clases',
    'profesor': 'Cursos & Clases',

    'fotografia': 'Servicio de Foto & Video',
    'fotografo': 'Servicio de Foto & Video',

    'peluqueria': 'Peluquería / Barbería / Belleza',
    'barberia': 'Peluquería / Barbería / Belleza',
    'belleza': 'Peluquería / Barbería / Belleza',
    'salon': 'Peluquería / Barbería / Belleza',

    'gimnasio': 'Gimnasio / Masaje / Entrenador',
    'masaje': 'Gimnasio / Masaje / Entrenador',
    'entrenador': 'Gimnasio / Masaje / Entrenador',

    'restaurante': 'Restaurantes / Gastronomía',
    'gastronomia': 'Restaurantes / Gastronomía',
    'comida': 'Restaurantes / Gastronomía',
    'pizza': 'Restaurantes / Gastronomía',
    'hamburguesa': 'Restaurantes / Gastronomía',

    'diseno': 'Diseño / Decoración',
    'disenador': 'Diseño / Decoración',

    'musica': 'Música / Animación / Shows',
    'animacion': 'Música / Animación / Shows',
    'dj': 'Música / Animación / Shows',

    # Material de Construcción
    'aire': 'Aires Acondicionados & Accesorios',
    'acondicionado': 'Aires Acondicionados & Accesorios',
    'split': 'Aires Acondicionados & Accesorios',

    'cemento': 'Cemento / Pegamento / Masilla',
    'pegamento': 'Cemento / Pegamento / Masilla',
    'masilla': 'Cemento / Pegamento / Masilla',

    'puerta': 'Puertas / Ventanas & Portones',
    'ventana': 'Puertas / Ventanas & Portones',
    'porton': 'Puertas / Ventanas & Portones',

    'azulejo': 'Mármol / Granito / Azulejos',
    'marmol': 'Mármol / Granito / Azulejos',
    'granito': 'Mármol / Granito / Azulejos',
    'baldosa': 'Mármol / Granito / Azulejos',

    # Empleo
    'empleo': 'Ofertas de Empleo',
    'trabajo': 'Ofertas de Empleo',
    'busco trabajo': 'Busco Trabajo',
}

# Default category wenn kein Match gefunden wird
DEFAULT_CATEGORY = 'Otros'

def map_category(revolico_category):
    """
    Mappt eine Revolico-Kategorie auf eine Rico-Cuba Kategorie

    Args:
        revolico_category (str): Revolico Kategorie Text

    Returns:
        str: Rico-Cuba Kategorie Name
    """
    if not revolico_category:
        return DEFAULT_CATEGORY

    # Normalize: lowercase und ohne Sonderzeichen
    category_lower = revolico_category.lower()

    # Suche nach Keywords in der Kategorie
    for keyword, rico_category in CATEGORY_MAPPINGS.items():
        if keyword in category_lower:
            return rico_category

    # Kein Match gefunden
    return DEFAULT_CATEGORY


def get_category_suggestions(revolico_category):
    """
    Gibt mehrere mögliche Kategorie-Matches zurück

    Args:
        revolico_category (str): Revolico Kategorie Text

    Returns:
        list: Liste von möglichen Rico-Cuba Kategorien
    """
    if not revolico_category:
        return [DEFAULT_CATEGORY]

    category_lower = revolico_category.lower()
    matches = []

    for keyword, rico_category in CATEGORY_MAPPINGS.items():
        if keyword in category_lower:
            if rico_category not in matches:
                matches.append(rico_category)

    return matches if matches else [DEFAULT_CATEGORY]
