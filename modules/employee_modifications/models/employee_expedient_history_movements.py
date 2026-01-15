from odoo import models, fields, api, _

class EmployeeExpedientLine(models.Model):
    _name = 'employee.expedient.line'
    _description = 'Línea de Historial de Movimientos'
    _order = 'fecha desc'

    expedient_id = fields.Many2one('employee.expedient', string="Expediente", ondelete='cascade')
    tipo_movimiento = fields.Selection([
        ('alta', 'Alta'),
        ('baja', 'Baja'),
        ('reingreso', 'Reingreso')
    ], string="Tipo", required=True)
    fecha = fields.Date(string="Fecha", required=True)
    motivo = fields.Text(string="Motivo/Detalle")