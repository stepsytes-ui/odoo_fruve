
from odoo import models, fields, api
from odoo.exceptions import ValidationError

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

        pending_resguardos = self.env['employee.resguardo'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['active', 'partial'])
        ])

        if pending_resguardos:
            pending_items = pending_resguardos.mapped('line_ids').filtered(lambda l: not l.devuelto)
            pending_names = ', '.join(pending_items.mapped('asset_id.nombre')[:10])
            if pending_names:
                raise ValidationError(
                    'No se puede registrar la baja. El empleado tiene resguardos activos pendientes de devolucion: %s'
                    % pending_names
                )
            raise ValidationError(
                'No se puede registrar la baja. El empleado tiene resguardos activos pendientes de devolucion.'
            )

        # 1. Buscar el expediente único del empleado
        expedient = self.env['employee.expedient'].search([('employee_id', '=', self.employee_id.id)], limit=1)
        
        if expedient:
            expedient._registrar_movimiento(
                'baja',
                self.fecha_movimiento,
                motivo=self.motivo_baja,
                user_id=self.env.user.id,
            )
            
            expedient.write({
                'hoja_renuncia_convenio': self.hoja_renuncia_convenio,
                'nombre_hoja_renuncia': self.nombre_hoja_renuncia,
                'recontratable': self.recontratable,
                'motivo_baja': self.motivo_baja,
            })

        # 4. Cambiar estado del empleado a inactivo PERO NO archivarlo todavía
        # Solo se archivará cuando se marque como finiquitado desde el formulario del empleado
        self.employee_id.write({
            'departure_reason_id': self.departure_reason_id.id,
            'departure_date': self.fecha_movimiento,
            'employee_status': 'inactive'
        })
        
        return {'type': 'ir.actions.act_window_close'}