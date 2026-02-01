#!/usr/bin/env python3
"""Generate PDF manual for Geotab Keyless Manager"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Colors
GEOTAB_BLUE = HexColor('#00A3E0')
DARK_BLUE = HexColor('#2c3e50')
LIGHT_GRAY = HexColor('#f8f9fa')
WHITE = HexColor('#ffffff')
WARNING_BG = HexColor('#fff3cd')
INFO_BG = HexColor('#d1ecf1')
SUCCESS_BG = HexColor('#d4edda')

def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=WHITE,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=GEOTAB_BLUE,
        spaceBefore=20,
        spaceAfter=10,
        borderColor=GEOTAB_BLUE,
        borderWidth=1,
        borderPadding=5
    ))

    styles.add(ParagraphStyle(
        name='SubsectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=DARK_BLUE,
        spaceBefore=15,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name='CodeText',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Courier',
        backColor=HexColor('#2d3748'),
        textColor=WHITE,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=5,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name='Warning',
        parent=styles['Normal'],
        fontSize=11,
        backColor=WARNING_BG,
        borderColor=HexColor('#ffc107'),
        borderWidth=1,
        borderPadding=8,
        leftIndent=10,
        spaceBefore=10,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name='Info',
        parent=styles['Normal'],
        fontSize=11,
        backColor=INFO_BG,
        borderColor=HexColor('#17a2b8'),
        borderWidth=1,
        borderPadding=8,
        leftIndent=10,
        spaceBefore=10,
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name='TOCEntry',
        parent=styles['Normal'],
        fontSize=12,
        leftIndent=20,
        spaceBefore=5
    ))

    return styles

def create_header(styles):
    """Create document header"""
    elements = []

    # Header background
    header_data = [[
        Paragraph('<b>Geotab Keyless Manager</b>', styles['MainTitle']),
    ], [
        Paragraph('Manual de Usuario v1.0', styles['Subtitle']),
    ], [
        Paragraph('Sistema de Gestion de Llaves Virtuales', styles['Subtitle']),
    ]]

    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GEOTAB_BLUE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))

    elements.append(header_table)
    elements.append(Spacer(1, 30))

    return elements

def create_toc(styles):
    """Create table of contents"""
    elements = []

    elements.append(Paragraph('Contenido', styles['SectionTitle']))

    toc_items = [
        '1. Introduccion',
        '2. Requisitos Previos',
        '3. Inicio de Sesion',
        '4. Gestion de Dispositivos',
        '5. Plantillas de Llaves Virtuales',
        '6. Crear Llaves Virtuales',
        '7. Eliminar Llaves Virtuales',
        '8. Registro de Actividad (Logs)',
        '9. Importacion CSV',
        '10. Solucion de Problemas',
    ]

    for item in toc_items:
        elements.append(Paragraph(item, styles['TOCEntry']))

    elements.append(Spacer(1, 20))
    return elements

def create_section(title, styles):
    return Paragraph(title, styles['SectionTitle'])

def create_subsection(title, styles):
    return Paragraph(title, styles['SubsectionTitle'])

def create_paragraph(text, styles):
    return Paragraph(text, styles['BodyText'])

def create_warning(text, styles):
    return Paragraph(f'<b>Advertencia:</b> {text}', styles['Warning'])

def create_info(text, styles):
    return Paragraph(f'<b>Info:</b> {text}', styles['Info'])

def create_bullet_list(items, styles):
    list_items = [ListItem(Paragraph(item, styles['BodyText'])) for item in items]
    return ListFlowable(list_items, bulletType='bullet', leftIndent=20)

def create_numbered_list(items, styles):
    list_items = [ListItem(Paragraph(item, styles['BodyText'])) for item in items]
    return ListFlowable(list_items, bulletType='1', leftIndent=20)

def create_table(headers, data, col_widths=None):
    table_data = [headers] + data

    if col_widths is None:
        col_widths = [8*cm, 8*cm]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GEOTAB_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#dddddd')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))

    return table

def build_document():
    doc = SimpleDocTemplate(
        'manual_usuario.pdf',
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = create_styles()
    elements = []

    # Header
    elements.extend(create_header(styles))

    # TOC
    elements.extend(create_toc(styles))
    elements.append(PageBreak())

    # Section 1: Introduction
    elements.append(create_section('1. Introduccion', styles))
    elements.append(create_paragraph(
        '<b>Geotab Keyless Manager</b> es una aplicacion web disenada para gestionar llaves virtuales '
        'en dispositivos Geotab equipados con tecnologia Keyless. Permite crear, administrar y eliminar '
        'llaves virtuales de forma masiva, facilitando la gestion de flotas de vehiculos.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Caracteristicas Principales', styles))
    elements.append(create_bullet_list([
        'Gestion multi-dispositivo con operaciones en lote',
        'Sistema de plantillas reutilizables para llaves virtuales',
        'Soporte para multiples bases de datos (multi-tenant)',
        'Registro completo de actividad (logs)',
        'Importacion de dispositivos desde CSV',
        'Interfaz intuitiva con indicadores de progreso',
    ], styles))

    # Section 2: Requirements
    elements.append(create_section('2. Requisitos Previos', styles))
    elements.append(create_subsection('Credenciales Necesarias', styles))
    elements.append(create_bullet_list([
        '<b>Base de datos:</b> Nombre de la base de datos Geotab asignada',
        '<b>Email:</b> Cuenta de usuario con permisos de administracion',
        '<b>Contrasena:</b> Contrasena de la cuenta Geotab',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Informacion de Dispositivos', styles))
    elements.append(create_bullet_list([
        'Numeros de serie de los dispositivos Keyless (formato: G9XXXXXXXX)',
        'Tags NFC autorizados (numeros de serie de tarjetas NFC)',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_warning('Cada dispositivo permite un maximo de 4 llaves virtuales simultaneas.', styles))

    # Section 3: Login
    elements.append(create_section('3. Inicio de Sesion', styles))
    elements.append(create_paragraph(
        'La seccion de autorizacion se encuentra en la parte superior izquierda de la aplicacion.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_numbered_list([
        '<b>Seleccionar Base de Datos:</b> Introduzca el nombre de la base de datos Geotab en el campo "Database".',
        '<b>Introducir Credenciales:</b> Complete los campos "Email" y "Password" con sus credenciales de Geotab.',
        '<b>Conectar:</b> Pulse el boton "Connect & Save".',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_info(
        'Al conectar correctamente, la barra superior mostrara "Sesion Activa" en verde y se cargaran los dispositivos disponibles.',
        styles
    ))

    # Section 4: Device Management
    elements.append(PageBreak())
    elements.append(create_section('4. Gestion de Dispositivos', styles))
    elements.append(create_subsection('Panel de Dispositivos', styles))
    elements.append(create_paragraph(
        'El panel central muestra la lista de dispositivos registrados con la siguiente informacion:',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_table(
        ['Columna', 'Descripcion'],
        [
            ['Serial', 'Numero de serie del dispositivo Geotab'],
            ['Descripcion', 'Nombre o descripcion del vehiculo'],
            ['Llaves', 'Numero de llaves virtuales activas (max. 4)'],
            ['Acciones', 'Botones para ver detalles y sincronizar'],
        ]
    ))
    elements.append(Spacer(1, 15))
    elements.append(create_subsection('Botones de Accion Global', styles))
    elements.append(create_bullet_list([
        '<b>Deploy Selected</b> (verde) - Crear llaves en dispositivos seleccionados',
        '<b>Sync All</b> (azul) - Sincronizar todos los dispositivos con Geotab',
        '<b>Delete Keys</b> (rojo) - Eliminar llaves de dispositivos seleccionados',
        '<b>Delete Devices</b> (naranja) - Eliminar dispositivos de la lista local',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Anadir Dispositivos Manualmente', styles))
    elements.append(create_numbered_list([
        'Introduzca el numero de serie y descripcion en los campos correspondientes.',
        'Pulse el boton "Add Device".',
    ], styles))

    # Section 5: Templates
    elements.append(create_section('5. Plantillas de Llaves Virtuales', styles))
    elements.append(create_paragraph(
        'Las plantillas permiten guardar configuraciones predefinidas de llaves virtuales para reutilizarlas '
        'facilmente. Cada plantilla incluye permisos, tags NFC autorizados y duracion por defecto.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Usar una Plantilla Existente', styles))
    elements.append(create_numbered_list([
        'Seleccione una plantilla del desplegable "Seleccionar Plantilla".',
        'La configuracion se cargara automaticamente en el editor de llaves virtuales, incluyendo los tags NFC.',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Crear Nueva Plantilla', styles))
    elements.append(create_numbered_list([
        'Pulse el boton "+ Nueva".',
        'Complete el formulario con: Nombre, Referencia Usuario, Tags NFC, Duracion y Configuracion JSON.',
        'Pulse "Guardar".',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Formato de Configuracion JSON', styles))
    elements.append(Paragraph(
        '{"permissions": ["Lock", "Unlock", "IgnitionInhibit", "IgnitionEnable"], '
        '"privileges": ["CheckinOverride"], "endBookConditions": ["IgnitionOff"]}',
        styles['CodeText']
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_info(
        'Al editar una plantilla existente, se crea automaticamente una nueva version. '
        'Las versiones anteriores se archivan pero permanecen consultables para auditoria.',
        styles
    ))

    # Section 6: Create Keys
    elements.append(PageBreak())
    elements.append(create_section('6. Crear Llaves Virtuales', styles))
    elements.append(create_subsection('Proceso de Creacion', styles))
    elements.append(create_numbered_list([
        '<b>Seleccionar dispositivos:</b> Marque las casillas de los dispositivos donde desea crear llaves.',
        '<b>Configurar la llave:</b> Seleccione una plantilla o configure manualmente. Ajuste la duracion con el slider (1-24 meses).',
        '<b>Desplegar:</b> Pulse "Deploy Selected".',
        '<b>Confirmar:</b> Verifique los dispositivos seleccionados y confirme la operacion.',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_warning(
        'El sistema verificara que ningun dispositivo supere el limite de 4 llaves virtuales antes de proceder.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Indicador de Progreso', styles))
    elements.append(create_paragraph(
        'Durante operaciones masivas, se muestra una barra de progreso indicando el numero de dispositivos procesados, '
        'el estado de cada operacion (exito/error) y un resumen final.',
        styles
    ))

    # Section 7: Delete Keys
    elements.append(create_section('7. Eliminar Llaves Virtuales', styles))
    elements.append(create_subsection('Eliminar Llaves Individuales', styles))
    elements.append(create_numbered_list([
        'Pulse en "Ver" junto al dispositivo para abrir el detalle.',
        'En el popup de llaves activas, pulse el boton de eliminar junto a la llave deseada.',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Eliminar Todas las Llaves (Masivo)', styles))
    elements.append(create_numbered_list([
        'Seleccione los dispositivos de los que desea eliminar todas las llaves.',
        'Pulse "Delete Keys".',
        'Confirme la operacion en el dialogo de confirmacion.',
    ], styles))
    elements.append(Spacer(1, 10))
    elements.append(create_warning(
        'Esta accion eliminara TODAS las llaves virtuales de los dispositivos seleccionados. Esta operacion no se puede deshacer.',
        styles
    ))

    # Section 8: Logs
    elements.append(create_section('8. Registro de Actividad (Logs)', styles))
    elements.append(create_paragraph(
        'El sistema mantiene un registro completo de todas las operaciones realizadas para auditoria y seguimiento.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Tipos de Acciones Registradas', styles))
    elements.append(create_table(
        ['Accion', 'Descripcion'],
        [
            ['CREATE_VK', 'Creacion de llave virtual'],
            ['DELETE_VK', 'Eliminacion de llave virtual'],
            ['DELETE_ALL_VK', 'Eliminacion masiva de llaves'],
            ['SYNC', 'Sincronizacion de dispositivo'],
            ['LOGIN', 'Inicio de sesion'],
            ['LOGOUT', 'Cierre de sesion'],
            ['RESET_LOGS', 'Limpieza del registro'],
        ]
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_paragraph(
        'Use el boton "Exportar CSV" para descargar el registro completo. '
        'Para limpiar el registro, pulse "Reset Log".',
        styles
    ))

    # Section 9: CSV Import
    elements.append(PageBreak())
    elements.append(create_section('9. Importacion CSV', styles))
    elements.append(create_paragraph(
        'Puede importar dispositivos masivamente desde un archivo CSV.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Formato del Archivo', styles))
    elements.append(Paragraph(
        'serial,descripcion<br/>G9C3E41234,Vehiculo Comercial 01<br/>G9C3E41235,Furgoneta Reparto',
        styles['CodeText']
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_info(
        '<b>Formato requerido:</b> Primera linea con cabecera (serial,descripcion), '
        'siguientes lineas con datos de dispositivos. Separador: coma. Codificacion: UTF-8.',
        styles
    ))
    elements.append(Spacer(1, 10))
    elements.append(create_subsection('Proceso de Importacion', styles))
    elements.append(create_numbered_list([
        'Pulse "Import CSV".',
        'Seleccione el archivo CSV con los dispositivos.',
        'Los dispositivos se anadiran a la lista automaticamente.',
    ], styles))

    # Section 10: Troubleshooting
    elements.append(create_section('10. Solucion de Problemas', styles))

    problems = [
        ('Error: "No Active Session"',
         'La sesion ha expirado o no se ha iniciado correctamente.',
         'Vuelva a introducir las credenciales y pulse "Connect & Save".'),
        ('Error: "Maximo 4 llaves por dispositivo"',
         'El dispositivo ya tiene 4 llaves virtuales activas.',
         'Elimine alguna llave existente antes de crear una nueva.'),
        ('Error: "Request failed"',
         'Error de comunicacion con el servidor Geotab Keyless.',
         'Verifique su conexion a internet y que las credenciales sean correctas.'),
        ('Dispositivo no aparece tras sincronizar',
         'El numero de serie puede ser incorrecto o el dispositivo no esta registrado en Geotab.',
         'Verifique el numero de serie en la plataforma Geotab.'),
        ('Tags NFC no se aplican',
         'Los tags NFC deben estar en formato correcto.',
         'Use el formato completo del serial NFC (ej: 7CF22JDPA1). Separe multiples tags con comas.'),
    ]

    for title, cause, solution in problems:
        elements.append(create_subsection(title, styles))
        elements.append(create_paragraph(f'<b>Causa:</b> {cause}', styles))
        elements.append(create_paragraph(f'<b>Solucion:</b> {solution}', styles))
        elements.append(Spacer(1, 5))

    # Footer
    elements.append(Spacer(1, 30))
    footer_data = [[
        Paragraph('<b>Geotab Keyless Manager</b><br/>Desarrollado para Vecttor<br/>Version 1.0 - Febrero 2026',
                  ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER, textColor=HexColor('#666666')))
    ]]
    footer_table = Table(footer_data, colWidths=[17*cm])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('LINEABOVE', (0, 0), (-1, 0), 1, HexColor('#dddddd')),
    ]))
    elements.append(footer_table)

    # Build PDF
    doc.build(elements)
    print('PDF generated: manual_usuario.pdf')

if __name__ == '__main__':
    build_document()
