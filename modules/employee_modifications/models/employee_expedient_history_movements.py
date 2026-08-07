from odoo import models, fields, api, _

class EmployeeExpedientLine(models.Model):
    _name = 'employee.expedient.line'
    _description = 'Línea de Historial de Movimientos'
    _order = 'fecha desc'

    expedient_id = fields.Many2one('employee.expedient', string="Expediente", ondelete='cascade')
    tipo_movimiento = fields.Selection([
        ('alta', 'Alta'),
        ('baja', 'Baja'),
        ('reingreso', 'Reingreso'),
        ('modificacion', 'Modificación')
    ], string="Tipo", required=True)
    fecha = fields.Date(string="Fecha", required=True)
    motivo = fields.Text(string="Motivo/Detalle")
    user_id = fields.Many2one(
        'res.users',
        string='Usuario que registró el movimiento',
        default=lambda self: self.env.user,
        readonly=True,
    )