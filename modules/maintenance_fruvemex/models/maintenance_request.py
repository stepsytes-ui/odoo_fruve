from odoo import models, fields, api

class FruveMaintenanceRequest(models.Model):
    _name = 'fruve.maintenance.request'
    _description = 'Solicitud / Orden de Mantenimiento'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    folio = fields.Char(string='Folio', required=True, readonly=True, default='Nuevo', copy=False)
    
    # Se usa self.env.user.id para garantizar que retorne un ID entero válido
    user_id = fields.Many2one(
        'res.users', 
        string='Registro', 
        default=lambda self: self.env.user.id, 
        readonly=True, 
        required=True
    )
    
    solicitante_id = fields.Many2one('hr.employee', string='Solicitante', required=True)
    area_id = fields.Many2one('hr.area', string='Área', required=True)
    descripcion = fields.Text(string='Descripción', required=True)
    
    clasificacion = fields.Selection([
        ('correctivo', 'Correctivo'),
        ('preventivo', 'Preventivo'),
        ('mejora', 'Mejora'),
        ('trabajo_temporal', 'Trabajo Temporal')
    ], string='Clasificación', required=True, default='correctivo')
    
    # Comodel actualizado a fruve.maintenance.type
    tipo_id = fields.Many2one('fruve.maintenance.type', string='Tipo', required=True)
    
    # Comodel actualizado a fruve.maintenance.technician
    technician_ids = fields.Many2many(
        'fruve.maintenance.technician',
        'fruve_maintenance_request_technician_rel',
        'request_id',
        'technician_id',
        string='Técnicos'
    )
    
    prioridad = fields.Selection([
        ('inmediata', 'Inmediata'),
        ('urgente', 'Urgente'),
        ('normal', 'Normal'),
        ('plan', 'Plan')
    ], string='Prioridad', default='normal', required=True)
    
    fecha_cierre = fields.Date(string='Fecha Cierre')
    
    # Comodel actualizado a fruve.maintenance.cancel.reason
    motivo_no_realizacion_id = fields.Many2one('fruve.maintenance.cancel.reason', string='Motivo de No Realización')
    
    tiempo_extra = fields.Boolean(string='Tiempo Extra', default=False)
    solucion = fields.Text(string='Solución')
    herramientas = fields.Text(string='Herramientas')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('folio', 'Nuevo') == 'Nuevo':
                vals['folio'] = self.env['ir.sequence'].next_by_code('fruve.maintenance.request') or 'Nuevo'
        return super().create(vals_list)