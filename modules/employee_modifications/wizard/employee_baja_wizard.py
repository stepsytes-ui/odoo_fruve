
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
    
    # Acción para crear el registro de baja
    def action_confirm_baja(self):
        self.ensure_one()
        
        # 1. Crear el registro en tu tabla de Expedientes
        self.env['employee.expedient'].create({
            'employee_id': self.employee_id.id,
            'tipo_registro': 'baja',
            'fecha_movimiento': self.fecha_movimiento,
            'motivo_baja': self.motivo_baja,
            'hoja_renuncia_convenio': self.hoja_renuncia_convenio,
            'nombre_hoja_renuncia': self.nombre_hoja_renuncia,
            'encuesta': self.encuesta,
            'nombre_encuesta': self.nombre_encuesta,
            'recontratable': self.recontratable,
        })

        # 2. Actualizar el empleado con la información de salida de Odoo y ARCHIVAR
        # Odoo usa 'departure_date', 'departure_reason_id' y 'departure_description'
        self.employee_id.write({
            'departure_date': self.fecha_movimiento,
            'departure_reason_id': self.departure_reason_id.id,
            'departure_description': self.motivo_baja,
            'employee_status': 'inactive',
            'active': False,  # Esto archiva al empleado automáticamente
        })

        return {'type': 'ir.actions.act_window_close'}