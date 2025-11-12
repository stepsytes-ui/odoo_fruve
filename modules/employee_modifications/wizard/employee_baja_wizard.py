
from odoo import models, fields, api

class EmployeeExpedientBajaWizard(models.TransientModel):
    _name = 'employee.expedient.baja.wizard'
    _description = 'Asistente para registro de Baja de Expediente'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)
    motivo_baja = fields.Text(string='Motivo/Razón de Baja/Renuncia', required=True)
    fecha_movimiento = fields.Date(string='Fecha de Movimiento', required=True, default=fields.Date.today)
    hoja_renuncia_convenio = fields.Binary(
        string='Hoja de Renuncia/Convenio (PDF)', 
        required=True, 
        attachment=True
    )
    nombre_hoja_renuncia = fields.Char(string='Nombre Archivo Renuncia', default='Renuncia_o_Convenio.pdf')
    acta_disciplinaria = fields.Binary(string='Acta Disciplinaria (Opcional)', attachment=True)
    nombre_acta_disciplinaria = fields.Char(string='Nombre Acta Disciplinaria', default='Acta_Disciplinaria.pdf')
    recontratable = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('n/a', 'N/A'),
    ], string='Es recontratable?', default='n/a', required=True)
    
    # Acción para crear el registro de baja
    def action_confirm_baja(self):
        self.ensure_one()
        
        # 1. Crear el registro de Expediente (tipo baja)
        expedient = self.env['employee.expedient'].create({
            'employee_id': self.employee_id.id,
            'tipo_registro': 'baja',
            'fecha_movimiento': self.fecha_movimiento,
            'motivo_baja': self.motivo_baja,
            'hoja_renuncia_convenio': self.hoja_renuncia_convenio,
            'nombre_hoja_renuncia': self.nombre_hoja_renuncia,
            'acta_disciplinaria': self.acta_disciplinaria,
            'nombre_acta_disciplinaria': self.nombre_acta_disciplinaria,
            'recontratable': self.recontratable,

        })

        self.employee_id.write({'employee_status': 'inactive'})

        return {'type': 'ir.actions.act_window_close'}