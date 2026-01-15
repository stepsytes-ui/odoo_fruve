
from odoo import models, fields, api

class EmployeeExpedientBajaWizard(models.TransientModel):
    _name = 'employee.expedient.baja.wizard'
    _description = 'Asistente para registro de Baja de Expediente'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, readonly=True)

    motivo_baja = fields.Text(string='Motivo/Razón de Baja/Renuncia', required=True)
    fecha_movimiento = fields.Date(string='Fecha de Movimiento', required=True, default=fields.Date.today)

    departure_reason_id = fields.Many2one(
        'hr.departure.reason', 
        string='Motivo de Salida (Odoo)', 
        required=True,
        help="Categoría oficial de Odoo para la baja"
    )

    hoja_renuncia_convenio = fields.Binary(
        string='Hoja de Renuncia/Convenio (PDF)', 
        required=False, 
        attachment=True
    )
    nombre_hoja_renuncia = fields.Char(string='Nombre Archivo Renuncia', default='Renuncia_o_Convenio.pdf')
    encuesta = fields.Binary(string='Encuesta (Opcional)', attachment=True)
    nombre_encuesta = fields.Char(string='Nombre Encuesta', default='Encuesta.pdf')
    recontratable = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No'),
        ('n/a', 'N/A'),
    ], string='Es recontratable?', default='n/a', required=True)
    
    def action_confirm_baja(self):
        self.ensure_one()
        # 1. Buscar el expediente único del empleado
        expedient = self.env['employee.expedient'].search([('employee_id', '=', self.employee_id.id)], limit=1)
        
        if expedient:
            # 2. Agregar la "Baja" al historial (la matriz)
            self.env['employee.expedient.line'].create({
                'expedient_id': expedient.id,
                'tipo_movimiento': 'baja',
                'fecha': self.fecha_movimiento,
                'motivo': self.motivo_baja,
            })
            
            # 3. Guardar los archivos en el expediente maestro
            expedient.write({
                'tipo_registro': 'baja',
                'hoja_renuncia_convenio': self.hoja_renuncia_convenio,
                'nombre_hoja_renuncia': self.nombre_hoja_renuncia,
                'recontratable': self.recontratable,
            })

        # 4. Archivar empleado (como hicimos antes)
        self.employee_id.write({
            'active': False,
            'departure_reason_id': self.departure_reason_id.id,
            'departure_date': self.fecha_movimiento,
            'employee_status': 'inactive'
        })
        return {'type': 'ir.actions.act_window_close'}