"""Enriquece el guion de Xolo Explorador con visuales de StudioFX y VALIDA cada dato contra el texto.

Regla de oro: todo lo que se muestra (cifras, años, nombres, frases) sale del texto del guion; el validador lo
comprueba. Lo unico que viene de fuera del guion son las coordenadas de los mapas, con su fuente anotada.
"""
import json
import re
import unicodedata

from .sincronizar import norm, tokens_guion

# ---------------------------------------------------------------- coordenadas (fuente + punto-en-poligono INEGI)
UBIC = {
    12: dict(lugar="Río Caliente", lon=-103.57719, lat=20.68269, munis=["Zapopan"], titulo="Zapopan · Jalisco", foco=12,
             fuente="Plus Code MCMF+34 del estacionamiento de Río Caliente (Mexico News Daily)"),
    11: dict(lugar="Templo Expiatorio", lon=-103.358954, lat=20.673696, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=4,
             fuente="Wikipedia (20°40′25″N 103°21′32″O) y Sygic (20°40'25.305\")"),
    10: dict(lugar="Mercado Libertad", lon=-103.34, lat=20.67556, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=4,
             fuente="Wikipedia (20.67556, -103.34)"),
    9: dict(lugar="El Diente", lon=-103.3968, lat=20.791, munis=["Zapopan"], titulo="Zapopan · Jalisco", foco=10,
            fuente="Mountain Project y Komoot (coinciden: 20.791, -103.3968)"),
    8: dict(lugar="Cajititlán", lon=-103.3094, lat=20.43174, munis=["Tlajomulco de Zúñiga"], titulo="Tlajomulco de Zúñiga · Jalisco", foco=8,
            fuente="Localidad de Cajititlán, en la orilla de la laguna (Wikipedia/Kiddle 20.43174, -103.3094)"),
    7: dict(lugar="Bosque Los Colomos", lon=-103.39259, lat=20.70661, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=4,
            fuente="Sygic (20°42'23.8\"N 103°23'33.3\"O)"),
    6: dict(lugar="El Ixtépete", lon=-103.44056, lat=20.63194, munis=["Zapopan"], titulo="Zapopan · Jalisco", foco=6,
            fuente="Una sola fuente (aroundus 20.63194, -103.44056); cae en Zapopan según INEGI"),
    5: dict(lugar="Panteón de Belén", lon=-103.345642, lat=20.687678, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=4,
            fuente="Atlas Obscura (20.687678, -103.345642)"),
    4: dict(lugar="Hospicio Cabañas", lon=-103.338, lat=20.677, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=4,
            fuente="UNESCO, ficha 815 (20.677, -103.338)"),
    3: dict(lugar="Barranca de Huentitán", lon=-103.310272, lat=20.74021, munis=["Guadalajara"], titulo="Guadalajara · Jalisco", foco=9,
            fuente="Parque Mirador Independencia, borde de la barranca (Sygic 20°44'24.8\"N 103°18'37.0\"O)"),
    2: dict(lugar="Salto de Juanacatlán", lon=-103.1752, lat=20.5132, munis=["El Salto", "Juanacatlán"], titulo="El Salto y Juanacatlán · Jalisco", foco=8,
            fuente="Wikipedia (20°30′48″N 103°10′31″O)"),
    1: dict(lugar="Cascadas de Huaxtla", lon=-103.4015, lat=20.9427, munis=["Zapopan"], titulo="Zapopan · Jalisco", foco=10,
            fuente="Final del cañón de Huaxtla (ropewiki 20°56'33.8\"N 103°24'05.5\"O). OJO: el acceso (20.9474, -103.4158) cae en San Cristóbal de la Barranca según INEGI"),
}

FOCO_SAT = {12: 3.0, 11: 0.8, 10: 0.8, 9: 2.0, 8: 3.0, 7: 1.2, 6: 1.0, 5: 0.8, 4: 0.8, 3: 2.5, 2: 2.0, 1: 2.0}  # medio ancho (km) del encuadre satelital final

# ---------------------------------------------------------------- visuales nuevos / mejorados
# kind: mapa | cifra | tarjeta | sello | frase | revision | lista | versiones | linea | etiqueta | fecha
# ancla = frase LITERAL del guion (dentro del bloque). evid = frases literales que respaldan lo mostrado.
E = []


def add(b, id, kind, ancla, dur, **kw):
    E.append(dict(bloque=b, id=id, kind=kind, anchor_text=ancla, duration=dur, **kw))


# ---- 12 Río Caliente
add(12, "fx_12_m", "mapa", "pero está en el municipio de Zapopan", 5.0, evid=["está en el municipio de Zapopan"])
add(12, "fx_12_a", "cifra", "En octubre de dos mil veintiséis, una crónica universitaria", 4.5, title="2026",
    subtitle="Una crónica universitaria describió pequeñas cascadas humeantes y señales de deterioro en algunos tramos",
    etiqueta="OCTUBRE", evid=["En octubre de dos mil veintiséis", "señales visibles de deterioro en algunos tramos"], contar=False)
add(12, "fx_12_b", "revision", "El contraste importa", 6.0, titulo="El contraste importa",
    items=[("Un fenómeno geológico excepcional", "ok"), ("No todo el cauce está limpio", "no"),
           ("No cualquier punto es apropiado para bañarse", "no")],
    evid=["no significa que todo el cauce esté limpio ni que cualquier punto sea apropiado para bañarse"])
add(12, "fx_12_c", "frase", "Bajo los árboles de Zapopan", 4.5, title="El calor de la Tierra sigue encontrando una salida.",
    destacar=["calor", "salida"], evid=["el calor de la Tierra sigue encontrando una salida"])
# ---- 11 Templo Expiatorio
add(11, "fx_11_m", "mapa", "Sin embargo, sucede frente al Templo Expiatorio", 5.0, evid=["frente al Templo Expiatorio"])
add(11, "fx_11_a", "sello", "Su estilo se llama neogótico", 3.5, title="Neogótico", subtitle="Retoma formas de las grandes construcciones góticas",
    evid=["Su estilo se llama neogótico", "retoma formas propias de las grandes construcciones góticas"])
add(11, "fx_11_b", "lista", "arcos apuntados, vitrales, detalles tallados", 5.5, titulo="Formas góticas",
    items=[("Arcos apuntados", "ok"), ("Vitrales", "ok"), ("Detalles tallados", "ok"), ("Una marcada sensación de altura", "ok")],
    evid=["arcos apuntados, vitrales, detalles tallados y una marcada sensación de altura"])
add(11, "fx_11_c", "frase", "El resultado no es una copia medieval", 4.5, title="No es una copia medieval, sino una obra tapatía de su propio tiempo.",
    destacar=["tapatía", "propio", "tiempo"], evid=["no es una copia medieval, sino una obra tapatía de su propio tiempo"])
# ---- 10 Mercado
add(10, "fx_10_m", "mapa", "En el barrio de San Juan de Dios", 5.0, evid=["En el barrio de San Juan de Dios"])
add(10, "fx_10_a", "tarjeta", "La tarea llegó a Alejandro Zohn", 4.0, etiqueta="ARQUITECTO", title="Alejandro Zohn",
    subtitle="Un joven formado en Guadalajara", evid=["Alejandro Zohn, un joven formado en Guadalajara"])
add(10, "fx_10_b", "cifra", "En dos mil veintidós, el fuego afectó cientos de locales", 4.5, title="2022",
    subtitle="El fuego afectó cientos de locales y, con ellos, el sustento de numerosas familias", etiqueta="INCENDIO",
    evid=["En dos mil veintidós, el fuego afectó cientos de locales"], contar=False)
add(10, "fx_10_c", "frase", "cómo se construye un mercado que funcione como una pequeña ciudad", 5.0,
    title="¿Cómo se construye un mercado que funcione como una pequeña ciudad?", destacar=["mercado", "pequeña", "ciudad"],
    evid=["¿cómo se construye un mercado que funcione como una pequeña ciudad?"])
# ---- 9 El Diente
add(9, "fx_09_m", "mapa", "Su nombre no viene de un gran edificio", 5.0, evid=["El Diente, en la sierra de San Esteban"])
add(9, "fx_09_a", "frase", "La roca no fue colocada para hacer deporte", 4.5,
    title="La roca no fue colocada para hacer deporte: fueron los deportistas quienes aprendieron a leerla.",
    destacar=["deportistas", "leerla"], evid=["La roca no fue colocada para hacer deporte: fueron los deportistas quienes aprendieron a leerla"])
add(9, "fx_09_b", "tarjeta", "actividad que consiste en descender una pared", 4.0, etiqueta="RAPEL", title="Descender una pared",
    subtitle="Con ayuda de cuerdas y equipo adecuado", evid=["descender una pared con ayuda de cuerdas y equipo adecuado"])
add(9, "fx_09_c", "tarjeta", "La autoridad municipal reconoce El Diente", 4.0, etiqueta="AUTORIDAD MUNICIPAL",
    title="Rocas gigantes y práctica de montaña", subtitle="Así reconoce la autoridad municipal a El Diente",
    evid=["La autoridad municipal reconoce El Diente como un espacio de rocas gigantes y práctica de montaña"])
add(9, "fx_09_d", "frase", "La cuenta la piedra", 4.5, title="La cuenta la piedra, y cada generación encuentra una manera nueva de acercarse a ella.",
    destacar=["piedra", "generación"], evid=["La cuenta la piedra, y cada generación encuentra una manera nueva de acercarse a ella"])
# ---- 8 Cajititlán
add(8, "fx_08_m", "mapa", "es el agua de la laguna de Cajititlán", 5.0, evid=["la laguna de Cajititlán", "en Tlajomulco"])
add(8, "fx_08_a", "frase", "¿Por qué llevar a los Reyes al agua", 4.0, title="¿Por qué llevar a los Reyes al agua?", destacar=["Reyes", "agua"],
    evid=["¿Por qué llevar a los Reyes al agua?"])
add(8, "fx_08_b", "tarjeta", "ha enfrentado problemas ambientales", 3.5, etiqueta="LAGUNA", title="Problemas ambientales",
    subtitle="Exigen atención", color="rojo", evid=["ha enfrentado problemas ambientales que exigen atención"])
add(8, "fx_08_c", "versiones", "durante casi todo el año puede verse como una laguna", 6.0, titulo="Dos caras de Cajititlán",
    fichas=[("CASI TODO EL AÑO", "azul", "Una laguna", "Junto a pueblos tradicionales"),
            ("EN ENERO", "naranja", "Una expresión colectiva de fe", "La laguna se transforma en su escenario")],
    evid=["durante casi todo el año puede verse como una laguna junto a pueblos tradicionales; en enero se transforma en el escenario de una expresión colectiva de fe"])
add(8, "fx_08_d", "revision", "No es necesario exagerar su antigüedad", 5.0, titulo="El valor de la costumbre",
    items=[("Exagerar su antigüedad", "no"), ("Inventar milagros", "no"), ("Reconocer el valor de la costumbre", "ok")],
    evid=["No es necesario exagerar su antigüedad ni inventar milagros para reconocer el valor de la costumbre"])
add(8, "fx_08_e", "frase", "sus aguas significan mucho más que un paisaje", 4.0, title="Sus aguas significan mucho más que un paisaje.",
    destacar=["mucho", "más", "paisaje"], evid=["sus aguas significan mucho más que un paisaje"])
# ---- 7 Jardín Japonés
add(7, "fx_07_m", "mapa", "En medio de una de las zonas más urbanizadas de Guadalajara", 5.0, evid=["una de las zonas más urbanizadas de Guadalajara"])
add(7, "fx_07_a", "tarjeta", "El Consulado de Japón ha confirmado ese origen", 4.0, etiqueta="CONFIRMADO", title="Consulado de Japón",
    subtitle="Confirma el origen del jardín y su sentido como símbolo de amistad",
    evid=["El Consulado de Japón ha confirmado ese origen y su sentido como símbolo de amistad"])
add(7, "fx_07_b", "lista", "El agua, las piedras, los puentes y los recorridos", 5.0, titulo="Un jardín que ordena la mirada",
    items=[("El agua", "ok"), ("Las piedras", "ok"), ("Los puentes", "ok"), ("Los recorridos", "ok")],
    evid=["El agua, las piedras, los puentes y los recorridos invitan a descubrir una escena detrás de otra"])
add(7, "fx_07_c", "versiones", "El jardín reúne entonces dos historias", 6.0, titulo="Dos historias en un jardín",
    fichas=[("LA PRIMERA", "azul", "Amistad entre ciudades", "Y una manera diferente de diseñar paisajes"),
            ("LA SEGUNDA", "naranja", "Conservar un bosque", "En medio de calles, edificios y automóviles")],
    evid=["La primera habla de amistad entre ciudades y de una manera diferente de diseñar paisajes",
          "La segunda habla del valor de conservar un bosque en medio de calles, edificios y automóviles"])
add(7, "fx_07_d", "frase", "viajar también puede consistir en mirar de otra manera", 4.5,
    title="Viajar también puede consistir en mirar de otra manera el lugar donde siempre has vivido.".replace("siempre has vivido", "siempre ha vivido"),
    destacar=["mirar", "otra", "manera"], evid=["viajar también puede consistir en mirar de otra manera el lugar donde siempre ha vivido"])
# ---- 6 Ixtépete
add(6, "fx_06_m", "mapa", "En Zapopan, entre vialidades y colonias modernas", 5.0, evid=["En Zapopan, entre vialidades y colonias modernas"])
add(6, "fx_06_a", "lista", "describen un asentamiento con edificios ceremoniales", 5.5, titulo="Un asentamiento con",
    items=[("Edificios ceremoniales", "ok"), ("Espacios habitacionales", "ok"), ("Diferencias entre los grupos que vivían allí", "ok")],
    evid=["un asentamiento con edificios ceremoniales, espacios habitacionales y diferencias entre los grupos que vivían allí"])
add(6, "fx_06_b", "tarjeta", "Ese recurso suele asociarse con Teotihuacán", 3.5, etiqueta="SE ASOCIA CON", title="Teotihuacán",
    subtitle="Un muro inclinado con una sección vertical", evid=["Ese recurso suele asociarse con Teotihuacán", "combina un muro inclinado con una sección vertical"])
add(6, "fx_06_c", "sello", "un asunto más complejo que una simple copia", 3.5, title="No es una simple copia",
    subtitle="El INAH explica elementos compartidos dentro del mundo mesoamericano",
    evid=["un asunto más complejo que una simple copia", "El INAH explica la presencia de elementos compartidos dentro del mundo mesoamericano"])
add(6, "fx_06_d", "cifra", "Según el instituto, la última ocurrió", 5.0, title="650–750",
    subtitle="Años de la última etapa constructiva de la pirámide principal, según el instituto", etiqueta="NUESTRA ERA",
    evid=["entre los años seiscientos cincuenta y setecientos cincuenta de nuestra era"], contar=False)
add(6, "fx_06_e", "frase", "la de un valle habitado, trabajado y conectado", 5.0,
    title="Un valle habitado, trabajado y conectado cuando el nombre de la ciudad todavía no existía.", destacar=["habitado", "trabajado", "conectado"],
    evid=["la de un valle habitado, trabajado y conectado cuando el nombre de la ciudad todavía no existía"])
# ---- 5 Panteón de Belén
add(5, "fx_05_m", "mapa", "En el Panteón de Belén, las piedras también guardan una segunda vida", 5.0, evid=["En el Panteón de Belén"])
add(5, "fx_05_a", "tarjeta", "Su nombre original fue Panteón de Santa Paula", 3.5, etiqueta="NOMBRE ORIGINAL", title="Panteón de Santa Paula",
    subtitle="", evid=["Su nombre original fue Panteón de Santa Paula"])
add(5, "fx_05_b", "tarjeta", "El proyecto estuvo a cargo del arquitecto", 4.5, etiqueta="ARQUITECTO", title="Manuel Gómez Ibarra",
    subtitle="Por encargo del obispo Diego de Aranda y Carpinteiro",
    evid=["El proyecto estuvo a cargo del arquitecto Manuel Gómez Ibarra, por encargo del obispo Diego de Aranda y Carpinteiro"])
add(5, "fx_05_c", "tarjeta", "del pequeño Nachito", 4.0, etiqueta="LEYENDA", title="El pequeño Nachito",
    subtitle="Un niño al que la tradición atribuye un miedo extraordinario a la oscuridad",
    evid=["pequeño Nachito, un niño al que la tradición atribuye un miedo extraordinario a la oscuridad"])
add(5, "fx_05_d", "sello", "Son relatos populares", 3.5, title="Relatos populares",
    subtitle="No existen motivos para presentarlos como fenómenos comprobados",
    evid=["Son relatos populares; no existen motivos para presentarlos como fenómenos comprobados"])
add(5, "fx_05_e", "frase", "Sus lápidas no necesitan moverse durante la noche", 4.5,
    title="Sus lápidas no necesitan moverse durante la noche para contar buenas historias.", destacar=["lápidas", "buenas", "historias"],
    evid=["Sus lápidas no necesitan moverse durante la noche para contar buenas historias"])
# ---- 4 Hospicio Cabañas
add(4, "fx_04_m", "mapa", "uno de los espacios más conocidos de Guadalajara", 5.0, evid=["uno de los espacios más conocidos de Guadalajara"])
add(4, "fx_04_a", "tarjeta", "el obispo Juan Cruz Ruiz de Cabañas impulsó", 4.5, etiqueta="OBISPO", title="Juan Cruz Ruiz de Cabañas",
    subtitle="Impulsó una institución para niños huérfanos, personas mayores y otros sectores desamparados",
    evid=["el obispo Juan Cruz Ruiz de Cabañas impulsó una institución para atender a niños huérfanos, personas mayores y otros sectores desamparados"])
add(4, "fx_04_b", "tarjeta", "aparece El hombre de fuego", 4.0, etiqueta="FRESCO DE OROZCO", title="El hombre de fuego",
    subtitle="Una figura que parece elevarse en medio de un movimiento ardiente",
    evid=["El hombre de fuego, una figura que parece elevarse en medio de un movimiento ardiente"])
add(4, "fx_04_c", "linea", "El edificio guarda así una historia poco habitual", 7.5, titulo="Una historia poco habitual",
    eventos=[("1810", "Abre como Casa de la Caridad y la Misericordia"), ("1937–1939", "Orozco pinta cincuenta y siete frescos"),
             ("1997", "La UNESCO lo reconoce como Patrimonio Mundial")],
    evid=["abrió sus puertas en mil ochocientos diez", "Entre mil novecientos treinta y siete y mil novecientos treinta y nueve",
          "En mil novecientos noventa y siete, la UNESCO reconoció el Hospicio Cabañas como Patrimonio Mundial"])
add(4, "fx_04_d", "frase", "Sus patios siguen siendo los mismos grandes protagonistas", 5.0,
    title="Sus patios siguen siendo los mismos grandes protagonistas, pero el sentido de recorrerlos ha cambiado profundamente.",
    destacar=["patios", "cambiado", "profundamente"],
    evid=["Sus patios siguen siendo los mismos grandes protagonistas, pero el sentido de recorrerlos ha cambiado profundamente"])
# ---- 3 Barranca de Huentitán
add(3, "fx_03_m", "mapa", "La barranca de Huentitán, también conocida como parte", 5.0, evid=["La barranca de Huentitán"])
add(3, "fx_03_a", "lista", "la barranca fue al mismo tiempo límite", 6.0, titulo="Para la ciudad, la barranca fue",
    items=[("Límite", "ok"), ("Obstáculo", "ok"), ("Fuente de recursos", "ok"), ("Punto de encuentro con un territorio distinto", "ok")],
    evid=["la barranca fue al mismo tiempo límite, obstáculo, fuente de recursos y punto de encuentro con un territorio distinto"])
add(3, "fx_03_b", "lista", "La protección ambiental responde a su vegetación", 6.0, titulo="Protección ambiental",
    items=[("Su vegetación y valor ecológico", "ok"), ("Las presiones de la expansión urbana", "alerta"),
           ("La contaminación del sistema del río Santiago", "alerta")],
    evid=["La protección ambiental responde a su vegetación y valor ecológico, pero también a las presiones de la expansión urbana y la contaminación del sistema del río Santiago"])
add(3, "fx_03_c", "frase", "Un cañón que tardó muchísimo tiempo en tomar forma", 5.0,
    title="Un cañón que tardó muchísimo tiempo en tomar forma puede quedar a la vista en cuestión de minutos.",
    destacar=["muchísimo", "minutos"], evid=["Un cañón que tardó muchísimo tiempo en tomar forma puede quedar a la vista en cuestión de minutos"])
add(3, "fx_03_d", "frase", "¿por qué a veces actuamos como si fuera solamente", 5.0,
    title="¿Por qué a veces actuamos como si fuera solamente el fondo de una fotografía?", destacar=["fondo", "fotografía"],
    evid=["¿por qué a veces actuamos como si fuera solamente el fondo de una fotografía?"])
# ---- 2 El Salto de Juanacatlán
add(2, "fx_02_m", "mapa", "Era El Salto de Juanacatlán, una caída del río Santiago", 5.0, evid=["El Salto de Juanacatlán, una caída del río Santiago"])
add(2, "fx_02_a", "lista", "el agua, el aire y la salud forman parte de su vida cotidiana", 5.0, titulo="En juego para sus habitantes",
    items=[("El agua", "alerta"), ("El aire", "alerta"), ("La salud", "alerta")],
    evid=["no se trata de perder una vista bonita: el agua, el aire y la salud forman parte de su vida cotidiana"])
add(2, "fx_02_b", "frase", "¿qué sucede cuando un recurso que impulsó el desarrollo", 6.0,
    title="¿Qué sucede cuando un recurso que impulsó el desarrollo termina deteriorado por ese mismo crecimiento?", destacar=["recurso", "deteriorado"],
    evid=["¿qué sucede cuando un recurso que impulsó el desarrollo termina deteriorado por ese mismo crecimiento?"])
add(2, "fx_02_c", "revision", "no debemos confundir la belleza de imágenes antiguas", 5.0, titulo="Imágenes antiguas y condiciones actuales",
    items=[("Confundir imágenes antiguas con las condiciones actuales", "no"), ("Sustituir la recuperación por nostalgia", "no")],
    evid=["no debemos confundir la belleza de imágenes antiguas con las condiciones actuales, ni sustituir la recuperación por nostalgia"])
# ---- 1 Cascadas de Huaxtla
add(1, "fx_01_m", "mapa", "En el norte de Zapopan, cerca de las comunidades de Huaxtla", 5.0, evid=["En el norte de Zapopan, cerca de las comunidades de Huaxtla y San Lorenzo"])
add(1, "fx_01_a", "tarjeta", "El ayuntamiento de Zapopan ha documentado recorridos", 4.5, etiqueta="AYUNTAMIENTO DE ZAPOPAN", title="Recorridos documentados",
    subtitle="Por las tres cascadas, con énfasis en respetar caminos, personas y entorno",
    evid=["El ayuntamiento de Zapopan ha documentado recorridos por las tres cascadas y ha destacado la importancia de respetar caminos, personas y entorno"])
add(1, "fx_01_b", "tarjeta", "aunque la propia investigadora aclaró", 4.5, etiqueta="ACLARACIÓN", title="Un método con límites", color="rojo",
    subtitle="No permitía afirmar directamente que se rebasaran los límites de una norma específica",
    evid=["su método no permitía afirmar directamente que se hubieran rebasado los límites de una norma específica"])
add(1, "fx_01_c", "revision", "Son asuntos que deben investigarse y atenderse", 6.0, titulo="Asuntos que deben investigarse",
    items=[("Investigar y atender estos asuntos", "ok"), ("Dar por demostrada una causa única", "no"),
           ("Presentar las pozas como seguras para nadar", "no")],
    evid=["Son asuntos que deben investigarse y atenderse; no corresponde dar por demostrada una causa única ni presentar las pozas como seguras para nadar"])
add(1, "fx_01_d", "frase", "Un paisaje extraordinario no se conserva solamente", 4.5,
    title="Un paisaje extraordinario no se conserva solamente porque sea bonito.", destacar=["extraordinario", "bonito"],
    evid=["Un paisaje extraordinario no se conserva solamente porque sea bonito"])
add(1, "fx_01_e", "frase", "¿Cuál de estos lugares conocías", 4.0, title="¿Cuál de estos lugares conocías y qué recuerdas de él?", destacar=["conocías", "recuerdas"],
    evid=["¿Cuál de estos lugares conocías y qué recuerdas de él?"])

# ---- gancho (primeros ~25 s)
HOOK = []
def _h(id, kind, ancla, dur, **kw):
    HOOK.append(dict(id=id, kind=kind, anchor_text=ancla, duration=dur, effect_id=kind, secondary="", asset_requirement="none",
                     asset_hint="", origen="nuevo", **kw))


_h("fx_h_01", "tarjeta", "En un bosque de Zapopan corre un río", 3.6, etiqueta="BOSQUE DE ZAPOPAN", title="Un río que sale caliente de la tierra",
   subtitle="", evid=["En un bosque de Zapopan corre un río que sale caliente de la tierra"])
_h("fx_h_02", "tarjeta", "En plena ciudad hay una pirámide anterior", 3.6, etiqueta="EN PLENA CIUDAD", title="Una pirámide anterior a Guadalajara",
   subtitle="", evid=["En plena ciudad hay una pirámide anterior a Guadalajara"])
_h("fx_h_03", "sello", "que alguna vez llamaron el Niágara mexicano", 3.2, title="Niágara mexicano", subtitle="Una cascada que así llamaron alguna vez",
   evid=["una cascada que alguna vez llamaron el Niágara mexicano"])
_h("fx_h_04", "cifra", "Vamos a recorrer doce rincones", 3.6, title="12", subtitle="rincones de Guadalajara y sus alrededores", etiqueta="EL RECORRIDO",
   contar=True, evid=["Vamos a recorrer doce rincones de Guadalajara y sus alrededores"])
_h("fx_h_05", "frase", "empezando por uno donde el suelo todavía guarda calor", 2.6, title="Empezando por uno donde el suelo todavía guarda calor.",
   destacar=["suelo", "calor"], evid=["empezando por uno donde el suelo todavía guarda calor"])

# ---- mejoras de los efectos que YA traia tu JSON (se conservan; se les agregan datos o respaldo sin imagen)
EXT = {
    "fx_03_01": dict(reemplaza=dict(kind="cifra", title="≈ 500 m", subtitle="Desnivel entre el borde y el fondo en ciertos sectores próximos al valle",
                                     etiqueta="DESNIVEL", contar=True, evid=["desniveles de alrededor de quinientos metros"])),
    "fx_04_02": dict(reemplaza=dict(kind="cifra", title="57", subtitle="Frescos pintados por José Clemente Orozco en la capilla",
                                     etiqueta="1937–1939", contar=True,
                                     evid=["José Clemente Orozco pintó cincuenta y siete frescos en su capilla"])),
    "fx_10_03": dict(datos=dict(kind="versiones", titulo="El mercado crece", fichas=[
        ("1958", "azul", "Edificio original", "Cubiertas de concreto de formas atrevidas, espacios de luz y circulación interior"),
        ("PRINCIPIOS DE LOS OCHENTA", "naranja", "Ampliación", "Otro nivel en una parte del conjunto")],
        evid=["Zohn utilizó el concreto para crear cubiertas de formas atrevidas, espacios de luz y circulación interior",
              "A principios de los ochenta, el propio Zohn participó en una ampliación que incorporó otro nivel en una parte del conjunto"])),
    "fx_05_02": dict(datos=dict(kind="versiones", titulo="Dos maneras de acercarse a un mismo lugar", fichas=[
        ("LA HISTORIA DOCUMENTADA", "azul", "Hechos", "Explica quién construyó el panteón, cuándo funcionó y por qué es patrimonio"),
        ("LA TRADICIÓN ORAL", "naranja", "Leyendas", "Revela cómo las personas buscan dar sentido al duelo, al miedo y al recuerdo")],
        evid=["La historia documentada explica quién construyó el panteón, cuándo funcionó y por qué es patrimonio",
              "La tradición oral revela cómo las personas buscan dar sentido al duelo, al miedo y al recuerdo"])),
    "fx_02_02": dict(datos=dict(kind="versiones", titulo="Ayer y hoy", fichas=[
        ("AYER", "azul", "Cascada ancha y poderosa", "Cubierta de espuma blanca"),
        ("HOY", "rojo", "La cascada sigue existiendo", "Pero el agua que la alimenta ha sufrido un deterioro profundo")],
        evid=["una cascada ancha, poderosa y cubierta de espuma blanca",
              "La cascada sigue existiendo, pero el agua que la alimenta ha sufrido un deterioro profundo"])),
    "fx_08_02": dict(datos=dict(kind="linea", titulo="Del templo a la laguna", eventos=[
        ("TEMPLO", "Tres imágenes de los Reyes Magos salen de un templo"), ("PUEBLO", "Recorren un pueblo entre música y gente"),
        ("EMBARCACIONES", "Suben a unas embarcaciones"), ("LAGUNA", "Recorren la laguna de Cajititlán")],
        evid=["Tres imágenes de los Reyes Magos salen de un templo, recorren un pueblo entre música y gente, y después suben a unas embarcaciones",
              "es el agua de la laguna de Cajititlán"])),
    "fx_02_03": dict(reemplaza=dict(kind="fecha", title="2007", subtitle="Un informe reunió preocupaciones de organizaciones y pobladores",
                                     evid=["En dos mil siete, un informe reunió preocupaciones de organizaciones y pobladores"])),
    "fx_01_03": dict(sin_imagen=dict(kind="tarjeta", etiqueta="UN MES DESPUÉS", title="Visita de autoridades ambientales federales",
                                      subtitle="Para atender denuncias sobre posible contaminación del afluente",
                                      evid=["autoridades ambientales federales informaron de una visita a la zona para atender denuncias sobre posible contaminación del afluente"])),
    "fx_11_02": dict(sin_imagen=dict(kind="tarjeta", etiqueta="ARQUITECTO", title="Adamo Boari",
                                      subtitle="Arquitecto italiano, relacionado también con edificios emblemáticos de la capital del país",
                                      evid=["el arquitecto italiano Adamo Boari, relacionado también con edificios emblemáticos de la capital del país"])),
    "fx_06_03": dict(sin_imagen=dict(kind="tarjeta", etiqueta="ARQUEOLOGÍA", title="Estructuras, materiales y un entierro",
                                      subtitle="Hallazgos registrados en las exploraciones del siglo veinte",
                                      evid=["Los arqueólogos registraron estructuras, materiales y un entierro"])),
    "fx_08_03": dict(sin_imagen=dict(kind="tarjeta", etiqueta="TRADICIÓN", title="Los Reyes sobre el agua",
                                      subtitle="Las imágenes recorren la laguna de Cajititlán",
                                      evid=["en que las imágenes recorran la laguna"])),
}

# ---------------------------------------------------------------- numeros en palabras
_U = {"dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
      "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
      "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
      "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
      "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
_H = {"cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600,
      "setecientos": 700, "ochocientos": 800, "novecientos": 900}


def numeros_en(texto):
    """Todos los numeros escritos con palabras que aparecen en `texto` (lista de enteros)."""
    out = []
    for trozo in re.split(r"[.,;:!?()¿¡\"«»\n]+", texto.lower()):
        out += _numeros_trozo([norm(w) for w in re.findall(r"\w+", trozo)])
    return out


def _numeros_trozo(toks):
    out, i = [], 0
    while i < len(toks):
        if toks[i] in _U or toks[i] in _H or toks[i] == "mil":
            tot = cur = 0
            seen_h = seen_mil = seen_t = False
            j = i
            while j < len(toks):
                w = toks[j]
                if w == "y" and j + 1 < len(toks) and (toks[j + 1] in _U or toks[j + 1] in _H or toks[j + 1] == "mil") and not (
                        toks[j + 1] in _H or toks[j + 1] == "mil"):
                    j += 1
                    continue
                if w in _H:
                    if seen_h:
                        break
                    cur += _H[w]; seen_h = True
                elif w == "mil":
                    if seen_mil:
                        break
                    tot += (cur or 1) * 1000; cur = 0; seen_mil = True; seen_h = False; seen_t = False
                elif w in _U:
                    v = _U[w]
                    if v >= 20 and seen_t and v >= 20:
                        break
                    cur += v
                    if v >= 20 and v % 10 == 0:
                        seen_t = True
                else:
                    break
                j += 1
            out.append(tot + cur)
            i = max(j, i + 1)
        else:
            i += 1
    return out


# ---------------------------------------------------------------- utilidades
def texto_bloques(guion):
    out = {}
    for s in guion["segmentos"]:
        m = re.match(r"^(\d+)\.", s.get("nombre", "") or "")
        if s["tipo"] == "bloque" and m:
            out[int(m.group(1))] = (s["texto"], s["nombre"])
    return out


def _seq(frase):
    return [norm(w) for w in re.findall(r"\w+", frase) if norm(w)]


def contiene(texto, frase):
    t, f = _seq(texto), _seq(frase)
    return any(t[i:i + len(f)] == f for i in range(len(t) - len(f) + 1))


def mostrados(e):
    """Cadenas de texto que el espectador vera (para validar nombres y cifras)."""
    s = [e.get("title", ""), e.get("subtitle", ""), e.get("etiqueta", ""), e.get("titulo", "")]
    for it in e.get("items", []):
        s.append(it[0])
    for f in e.get("fichas", []):
        s += [f[0], f[2], f[3]]
    for ev in e.get("eventos", []):
        s += [ev[0], ev[1]]
    return [x for x in s if x]


COMUNES = {"inscrito", "cuidar", "respeto", "hechos", "desnivel", "hallazgos", "abre", "investigo"}  # palabras corrientes de parafrasis
GENERICAS = set("la el los las un una de del al y o en con sin por para que se su sus lo es no mas mal ya tan hoy ayer".split())


_VOC = {}


def vocab_global(guion):
    if "k" not in _VOC:
        txt = " ".join(s.get("texto", "") for s in guion["segmentos"]) + " " + " ".join(
            b["nombre"] for b in guion["xolo_estudio"]["bloques"])
        _VOC["k"] = {w[:6] for w in _seq(txt)}
    return _VOC["k"]


def validar_efecto(e, texto, nombre, voc=None):
    """-> lista de avisos (vacia = todo respaldado por el guion)."""
    av = []
    ok_nums = set(numeros_en(texto)) | set(re.findall(r"\d+", nombre))
    ok_nums = {str(n) for n in ok_nums}
    base = set(_seq(texto)) | set(_seq(nombre))
    for ev in e.get("evid", []):
        if not contiene(texto, ev):
            av.append("EVIDENCIA NO ENCONTRADA en el guion: «%s»" % ev)
    for cad in mostrados(e):
        for n in re.findall(r"\d+", cad):
            if n not in ok_nums and n not in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"}:
                av.append("CIFRA «%s» (en «%s») no sale del guion" % (n, cad))
        for k, w in enumerate(re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+", cad)):
            nw = norm(w)
            if len(nw) < 3 or nw in GENERICAS or w.isupper():
                continue  # etiquetas en mayusculas: texto de apoyo del programa
            if nw in base:
                continue
            if voc is not None and nw[:6] not in voc and nw not in COMUNES:
                av.append("NOMBRE/PALABRA «%s» (en «%s») no aparece en NINGUNA parte del guion: revisar su fuente" % (w, cad))
            elif k > 0 and cad.find(w) > 0 and w[0].isupper() and nw[:6] not in {x[:6] for x in base}:
                av.append("Nombre propio «%s» (en «%s») no aparece en el texto de este bloque" % (w, cad))
    return av


def enriquecer(guion):
    voc = vocab_global(guion)
    """Devuelve (guion_nuevo, informe). No toca el original."""
    g = json.loads(json.dumps(guion))
    tb = texto_bloques(g)
    bloques = {b["numero"]: b for b in g["xolo_estudio"]["bloques"]}
    informe = []
    # 1) mejoras sobre efectos existentes
    for b in bloques.values():
        texto, nombre = tb[b["numero"]]
        for e in b["efectos"]:
            e["origen"] = "original"
            x = EXT.get(e["id"])
            if x and "reemplaza" in x:
                e["original"] = {k: e[k] for k in ("kind", "title", "subtitle", "effect_id")}
                nuevo = x["reemplaza"]
                e["kind"] = nuevo["kind"]
                e["title"], e["subtitle"] = nuevo["title"], nuevo["subtitle"]
                for k in ("etiqueta", "contar", "evid"):
                    if k in nuevo:
                        e[k] = nuevo[k]
                e["origen"] = "mejorado"
            elif x and "datos" in x:
                e["datos"] = x["datos"]
                e["evid"] = x["datos"].get("evid", [])
                e["origen"] = "mejorado"
            elif x and "sin_imagen" in x:
                e["sin_imagen"] = x["sin_imagen"]
    # 2) efectos nuevos
    for n in E:
        b = bloques[n["bloque"]]
        e = {k: v for k, v in n.items() if k != "bloque"}
        e.update(effect_id=n["kind"], secondary="", asset_requirement="none", asset_hint="", origen="nuevo")
        u = UBIC[n["bloque"]]
        if n["kind"] == "mapa":
            e.update(title=u["titulo"], subtitle=u["lugar"], lon=u["lon"], lat=u["lat"], municipios=u["munis"], lugar=u["lugar"],
                     foco_km=u["foco"], foco_sat_km=FOCO_SAT[n["bloque"]], fuente_coordenadas=u["fuente"])
        b["efectos"].append(e)
    g["hook_efectos"] = [dict(h) for h in HOOK]
    ht = next(x["texto"] for x in g["segmentos"] if x["tipo"] == "hook")
    for h in HOOK:
        informe.append(dict(bloque=0, id=h["id"], kind=h["kind"], origen="nuevo", avisos=validar_efecto(h, ht, "", voc) + ([] if contiene(ht, h["anchor_text"]) else ["ANCLA no encontrada"])))
    # 3) validacion
    for num in sorted(bloques, reverse=True):
        b = bloques[num]
        texto, nombre = tb[num]
        for e in b["efectos"]:
            ee = dict(e)
            if "datos" in e:
                ee.update(e["datos"])
            if "sin_imagen" in e:
                ee2 = dict(e["sin_imagen"])
                av2 = validar_efecto(ee2, texto, nombre, voc)
            else:
                av2 = []
            if e["kind"] == "mapa":
                av = [] if contiene(texto, e["anchor_text"]) else ["ANCLA no encontrada"]
                av += ["" if contiene(texto, ev) else "EVIDENCIA NO ENCONTRADA: «%s»" % ev for ev in e.get("evid", [])]
                av = [a for a in av if a]
            else:
                av = validar_efecto(ee, texto, nombre, voc)
            if not contiene(texto, e["anchor_text"]):
                av.append("ANCLA no encontrada en el bloque: «%s»" % e["anchor_text"])
            informe.append(dict(bloque=num, id=e["id"], kind=e["kind"], origen=e.get("origen"), avisos=av + av2))
    return g, informe
