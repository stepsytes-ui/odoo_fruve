from odoo import models, fields, api, _

class EmployeeDisciplinaryRecord(models.Model):
    _name = 'employee.disciplinary.record'
    _description = 'Acta Disciplinaria de Empleado'
    _order = 'fecha_acta desc'
    _inherit = ['mail.thread']

    # Relación con el empleado
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Referencia',
        compute='_compute_name',
        store=True
    )
    
    fecha_acta = fields.Date(
        string='Fecha del Acta',
        required=True,
        default=fields.Date.today
    )
    
    motivo = fields.Text(string='Motivo/Infracción', required=True)
    
    acta_disciplinaria_file = fields.Binary(
        string='Archivo del Acta (PDF)',
        attachment=True,
        required=True,
    )
    
    nombre_archivo = fields.Char(string='Nombre del Archivo')
    
    # Nombre descriptivo
    @api.depends('employee_id', 'fecha_acta')
    def _compute_name(self):
        for record in self:
            employee_name = record.employee_id.name if record.employee_id else 'Nuevo'
            date_str = record.fecha_acta.strftime('%Y-%m-%d') if record.fecha_acta else 'Sin Fecha'
            record.name = f"Acta Disciplinaria - {employee_name} ({date_str})"