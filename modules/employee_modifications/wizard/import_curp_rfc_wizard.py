# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
import logging

_logger = logging.getLogger(__name__)


class ImportCurpRfcWizard(models.TransientModel):
    _name = 'import.curp.rfc.wizard'
    _description = 'Asistente para Importar CURP y RFC desde Excel'

    archivo_excel = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Archivo Excel con las columnas: Número de Empleado, Nombre, CURP, RFC (con homoclave)'
    )
    
    nombre_archivo = fields.Char(
        string='Nombre del Archivo'
    )
    
    resultado_importacion = fields.Html(
        string='Resultado de la Importación',
        readonly=True
    )
    
    state = fields.Selection([
        ('seleccionar', 'Seleccionar Archivo'),
        ('resultado', 'Resultado')
    ], default='seleccionar', string='Estado')
    
    empleados_actualizados = fields.Integer(
        string='Empleados Actualizados',
        readonly=True,
        default=0
    )
    
    empleados_no_encontrados = fields.Integer(
        string='Empleados No Encontrados',
        readonly=True,
        default=0
    )
    
    errores_count = fields.Integer(
        string='Errores',
        readonly=True,
        default=0
    )

    def action_importar(self):
        """Procesa el archivo Excel e importa los datos de CURP y RFC"""
        self.ensure_one()
        
        if not self.archivo_excel:
            raise UserError(_('Por favor seleccione un archivo Excel.'))
        
        try:
            # Decodificar el archivo
            file_content = base64.b64decode(self.archivo_excel)
            
            # Abrir el archivo Excel
            workbook = xlrd.open_workbook(file_contents=file_content)
            sheet = workbook.sheet_by_index(0)
            
            empleados_actualizados = 0
            empleados_no_encontrados = []
            errores = []
            
            resultado_html = "<h3>Resultado de la Importación</h3>"
            resultado_html += "<table class='table table-striped'>"
            resultado_html += "<thead><tr><th>Núm. Empleado</th><th>Nombre</th><th>Estado</th><th>Detalles</th></tr></thead>"
            resultado_html += "<tbody>"
            
            # Iterar sobre las filas (comenzando desde la fila 1 para saltar encabezados)
            for row_idx in range(1, sheet.nrows):
                try:
                    # Leer las columnas
                    numero_empleado = str(sheet.cell_value(row_idx, 0)).strip()
                    nombre_empleado = str(sheet.cell_value(row_idx, 1)).strip() if sheet.ncols > 1 else ''
                    curp = str(sheet.cell_value(row_idx, 2)).strip().upper() if sheet.ncols > 2 else ''
                    rfc = str(sheet.cell_value(row_idx, 3)).strip().upper() if sheet.ncols > 3 else ''
                    nss = str(sheet.cell_value(row_idx, 4)).strip() if sheet.ncols > 4 else ''
                    
                    # Limpiar valores numéricos de Excel (ej: 123.0 -> 123)
                    if '.' in numero_empleado and numero_empleado.replace('.', '').isdigit():
                        numero_empleado = str(int(float(numero_empleado)))
                    
                    # Validar que al menos tengamos el número de empleado
                    if not numero_empleado:
                        continue
                    
                    # Buscar el empleado por biometric_id
                    empleado = self.env['hr.employee'].search([
                        ('biometric_id', '=', numero_empleado)
                    ], limit=1)
                    
                    if not empleado:
                        empleados_no_encontrados.append({
                            'numero': numero_empleado,
                            'nombre': nombre_empleado
                        })
                        resultado_html += f"<tr class='table-warning'><td>{numero_empleado}</td><td>{nombre_empleado}</td>"
                        resultado_html += f"<td><span class='badge badge-warning'>No Encontrado</span></td>"
                        resultado_html += f"<td>El empleado con número {numero_empleado} no existe en el sistema</td></tr>"
                        continue
                    
                    # Preparar valores para actualizar
                    valores = {}
                    detalles = []
                    
                    # Actualizar CURP si se proporciona
                    if curp:
                        # Validar formato CURP (18 caracteres)
                        if len(curp) == 18:
                            valores['identification_id'] = curp
                            detalles.append(f"CURP: {curp}")
                        else:
                            errores.append({
                                'numero': numero_empleado,
                                'nombre': empleado.name,
                                'error': f'CURP inválido: {curp} (debe tener 18 caracteres)'
                            })
                            resultado_html += f"<tr class='table-danger'><td>{numero_empleado}</td><td>{empleado.name}</td>"
                            resultado_html += f"<td><span class='badge badge-danger'>Error</span></td>"
                            resultado_html += f"<td>CURP inválido: {curp} (debe tener 18 caracteres)</td></tr>"
                            continue
                    
                    # Actualizar RFC si se proporciona
                    if rfc:
                        # Validar formato RFC (12 o 13 caracteres)
                        if len(rfc) in [12, 13]:
                            # El RFC se guarda directamente en el empleado (Odoo 18)
                            valores['rfc'] = rfc
                            detalles.append(f"RFC: {rfc}")
                        else:
                            errores.append({
                                'numero': numero_empleado,
                                'nombre': empleado.name,
                                'error': f'RFC inválido: {rfc} (debe tener 12 o 13 caracteres)'
                            })
                            resultado_html += f"<tr class='table-danger'><td>{numero_empleado}</td><td>{empleado.name}</td>"
                            resultado_html += f"<td><span class='badge badge-danger'>Error</span></td>"
                            resultado_html += f"<td>RFC inválido: {rfc} (debe tener 12 o 13 caracteres)</td></tr>"
                            continue
                    
                    # Actualizar NSS si se proporciona
                    if nss:
                        # Limpiar valores numéricos de Excel (ej: 123.0 -> 123)
                        if '.' in nss and nss.replace('.', '').isdigit():
                            nss = str(int(float(nss)))
                        
                        # Validar formato NSS (11 dígitos)
                        if len(nss) == 11 and nss.isdigit():
                            valores['ssnid'] = nss
                            detalles.append(f"NSS: {nss}")
                        else:
                            errores.append({
                                'numero': numero_empleado,
                                'nombre': empleado.name,
                                'error': f'NSS inválido: {nss} (debe tener 11 dígitos)'
                            })
                            resultado_html += f"<tr class='table-danger'><td>{numero_empleado}</td><td>{empleado.name}</td>"
                            resultado_html += f"<td><span class='badge badge-danger'>Error</span></td>"
                            resultado_html += f"<td>NSS inválido: {nss} (debe tener 11 dígitos)</td></tr>"
                            continue
                    
                    # Actualizar el empleado si hay cambios
                    if valores:
                        empleado.write(valores)
                    
                    if detalles or rfc:
                        empleados_actualizados += 1
                        detalle_text = ', '.join(detalles)
                        resultado_html += f"<tr class='table-success'><td>{numero_empleado}</td><td>{empleado.name}</td>"
                        resultado_html += f"<td><span class='badge badge-success'>Actualizado</span></td>"
                        resultado_html += f"<td>{detalle_text}</td></tr>"
                    
                except Exception as e:
                    error_msg = str(e)
                    errores.append({
                        'numero': numero_empleado if 'numero_empleado' in locals() else 'N/A',
                        'nombre': nombre_empleado if 'nombre_empleado' in locals() else 'N/A',
                        'error': error_msg
                    })
                    resultado_html += f"<tr class='table-danger'><td>{numero_empleado if 'numero_empleado' in locals() else 'N/A'}</td>"
                    resultado_html += f"<td>{nombre_empleado if 'nombre_empleado' in locals() else 'N/A'}</td>"
                    resultado_html += f"<td><span class='badge badge-danger'>Error</span></td>"
                    resultado_html += f"<td>{error_msg}</td></tr>"
                    _logger.error(f"Error procesando fila {row_idx + 1}: {error_msg}")
            
            resultado_html += "</tbody></table>"
            
            # Resumen
            resultado_html += "<div class='mt-3'><h4>Resumen</h4>"
            resultado_html += f"<p><strong>Empleados Actualizados:</strong> <span class='badge badge-success'>{empleados_actualizados}</span></p>"
            resultado_html += f"<p><strong>Empleados No Encontrados:</strong> <span class='badge badge-warning'>{len(empleados_no_encontrados)}</span></p>"
            resultado_html += f"<p><strong>Errores:</strong> <span class='badge badge-danger'>{len(errores)}</span></p>"
            resultado_html += "</div>"
            
            # Actualizar el wizard con el resultado
            self.write({
                'state': 'resultado',
                'resultado_importacion': resultado_html,
                'empleados_actualizados': empleados_actualizados,
                'empleados_no_encontrados': len(empleados_no_encontrados),
                'errores_count': len(errores)
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'import.curp.rfc.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': self.env.context,
            }
            
        except xlrd.XLRDError as e:
            raise UserError(_('Error al leer el archivo Excel: %s') % str(e))
        except Exception as e:
            raise UserError(_('Error inesperado: %s') % str(e))
    
    def action_volver(self):
        """Volver a la pantalla de selección"""
        self.write({
            'state': 'seleccionar',
            'archivo_excel': False,
            'nombre_archivo': False,
            'resultado_importacion': False,
            'empleados_actualizados': 0,
            'empleados_no_encontrados': 0,
            'errores_count': 0
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.curp.rfc.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
    
    def action_cerrar(self):
        """Cerrar el wizard"""
        return {'type': 'ir.actions.act_window_close'}
