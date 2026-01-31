
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeExtension(models.Model):
    _inherit = 'hr.employee'

    fecha_ingreso_manual = fields.Date(
        string='Fecha de Ingreso',
        help="Campo para ingresar la fecha de ingreso del empleado si deja vacio tomara la fecha actual por default"
    )
    
    expedient_ids = fields.One2many(
        'employee.expedient', 
        'employee_id', 
        string='Historial de Movimientos'
    )

    disciplinary_record_ids = fields.One2many(
        'employee.disciplinary.record',
        'employee_id',
        string='Actas Disciplinarias'
    )

    warning_ids = fields.One2many(
        'employee.warning',
        'employee_id',
        string='Amonestaciones'
    )

    custom_overtime_ids = fields.One2many(
        'overtime',
        'employee_id',
        string='Solicitudes Tiempo Extra'
    )

    documents_ids = fields.One2many(
        'employee.documents',
        'employee_id',
        string='Archivos y Documentos'
    )

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for employee, vals in zip(employees, vals_list):
            fecha_alta = vals.get('fecha_ingreso_manual') or fields.Date.today()
            self.env['employee.expedient'].create({
                    'employee_id': employee.id,
                    'tipo_registro': 'alta',
                    'fecha_movimiento': fecha_alta,
                    'recontratable': 'n/a',
                    'company_id': employee.company_id.id,
                })
        return employees
    
    def action_open_expedient_baja_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de baja para el empleado %s", self.name)
        return {
            'name': "Registro de Baja de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.baja.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_baja_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
    
    def action_open_expedient_reingreso_wizard(self):
        self.ensure_one()
        _logger.info("🟢 Abriendo wizard de reingreso para el empleado %s", self.name)
        return {
            'name': "Registro de Reingreso de empleado",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient.reingreso.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('employee_modifications.view_employee_expedient_reingreso_wizard_form').id,
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
    
    def action_view_expedient(self):
        self.ensure_one()
        expedient = self.env['employee.expedient'].search([
            ('employee_id', '=', self.id)
        ], limit=1)
        
        if not expedient:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No se encontró expediente para este empleado.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'name': f"Expediente de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.expedient',
            'view_mode': 'form',
            'res_id': expedient.id,
            'target': 'current',
        }
    
    def action_view_warnings(self):
        """Método para abrir la vista de amonestaciones del empleado"""
        self.ensure_one()
        return {
            'name': f"Amonestaciones de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.warning',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'default_biometric_id': self.biometric_id,
            },
            'target': 'current',
        }
    
    def action_view_overtime(self):
        """Método para abrir la vista de tiempo extra del empleado"""
        self.ensure_one()
        return {
            'name': f"Tiempo Extra de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'overtime',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
            },
            'target': 'current',
        }
    
    def action_view_documents(self):
        """Método para abrir los archivos y documentos del empleado"""
        self.ensure_one()
        # Buscar o crear el registro de documentos para este empleado
        document = self.env['employee.documents'].search([
            ('employee_id', '=', self.id)
        ], limit=1)
        
        if not document:
            # Crear automáticamente el registro si no existe
            document = self.env['employee.documents'].create({
                'employee_id': self.id,
            })
        
        return {
            'name': f"Archivos de {self.name}",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.documents',
            'view_mode': 'form',
            'res_id': document.id,
            'target': 'current',
        }