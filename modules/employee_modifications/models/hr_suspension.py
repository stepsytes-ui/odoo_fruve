# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
import pytz


class HrSuspension(models.Model):
    _name = 'hr.suspension'
    _description = 'Suspensión de Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nueva'),
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        tracking=True,
        index=True
    )
    
    biometric_id = fields.Char(
        string='Número de Empleado',
        related='employee_id.biometric_id',
        store=True,
        readonly=True
    )
    
    employee_name = fields.Char(
        string='Nombre del Empleado',
        related='employee_id.name',
        store=True,
        readonly=True
    )
    
    supervisor_id = fields.Many2one(
        'res.users',
        string='Supervisor',
        domain=lambda self: [('groups_id', 'in', [self.env.ref('overtime.group_overtime_supervisor').id])],
        tracking=True,
        help='Supervisor asignado (debe pertenecer al grupo Supervisor Tiempo Extra)'
    )
    
    date_from = fields.Date(
        string='Fecha Inicio',
        tracking=True
    )
    
    date_to = fields.Date(
        string='Fecha Fin',
        tracking=True,
        help='Fecha de fin de la suspensión'
    )
    
    modality = fields.Selection([
        ('continuous', 'Suspensión Continua'),
        ('non_continuous', 'Suspensión No Continua')
    ], string='Modalidad', default='continuous', required=True, tracking=True,
        help='Tipo de suspensión: continua (rango de fechas) o no continua (fechas individuales)')
    
    suspension_line_ids = fields.One2many(
        'hr.suspension.line',
        'suspension_id',
        string='Fechas de Suspensión',
        tracking=True,
        help='Fechas individuales de suspensión para suspensiones no continuas'
    )
    
    reason = fields.Text(
        string='Motivo de la Suspensión',
        required=True,
        tracking=True
    )
    
    leave_id = fields.Many2one(
        'hr.leave',
        string='Ausencia Origen',
        readonly=True,
        help='Ausencia de hr.leave que originó esta suspensión'
    )
    
    leave_ids = fields.One2many(
        'hr.leave',
        'suspension_id',
        string='Ausencias Relacionadas',
        readonly=True,
        help='Ausencias de tipo Suspensión creadas por este registro'
    )
    
    leave_count = fields.Integer(
        string='Cantidad de Ausencias',
        compute='_compute_leave_count',
        help='Cantidad de ausencias relacionadas creadas'
    )
    
    notes = fields.Html(
        string='Notas Adicionales',
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmada'),
        ('validate', 'Aprobada'),
        ('refuse', 'Rechazada'),
        ('cancel', 'Cancelada')
    ], string='Estado', default='draft', tracking=True, required=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    notes = fields.Html(
        string='Notas Adicionales',
        tracking=True
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    @api.depends('modality', 'suspension_line_ids', 'suspension_line_ids.suspension_date')
    def _compute_leave_count(self):
        """Calcula la cantidad de ausencias relacionadas"""
        for suspension in self:
            suspension.leave_count = len(suspension.leave_ids)

    @api.constrains('date_from', 'date_to', 'modality', 'suspension_line_ids')
    def _check_dates(self):
        """Valida las fechas según la modalidad"""
        for suspension in self:
            if suspension.modality == 'continuous':
                # Para suspensión continua, requiere fechas explícitas
                if not suspension.date_from or not suspension.date_to:
                    raise ValidationError(
                        _('Para una suspensión continua debe especificar fecha de inicio y fin.')
                    )
                if suspension.date_to < suspension.date_from:
                    raise ValidationError(
                        _('La fecha de fin debe ser posterior a la fecha de inicio.')
                    )
            elif suspension.modality == 'non_continuous':
                # Para suspensión no continua, requiere al menos una línea
                if not suspension.suspension_line_ids:
                    raise ValidationError(
                        _('Para una suspensión no continua debe agregar al menos una fecha en la tabla.')
                    )
                # date_from y date_to pueden estar vacíos en non_continuous

    @api.constrains('employee_id', 'date_from', 'date_to', 'suspension_line_ids', 'modality')
    def _check_overlapping_suspensions(self):
        """Valida que no existan suspensiones superpuestas para el mismo empleado"""
        for suspension in self:
            if suspension.state in ['cancel', 'refuse']:
                continue
            
            if suspension.modality == 'continuous':
                domain = [
                    ('employee_id', '=', suspension.employee_id.id),
                    ('id', '!=', suspension.id),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('modality', '=', 'continuous'),
                    ('date_from', '<=', suspension.date_to),
                    ('date_to', '>=', suspension.date_from),
                ]
                
                overlapping = self.search(domain, limit=1)
                if overlapping:
                    raise ValidationError(
                        _('Ya existe una suspensión para %s en el período del %s al %s.') % (
                            suspension.employee_id.name,
                            overlapping.date_from,
                            overlapping.date_to
                        )
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generar el folio automáticamente al crear una suspensión y llenar fechas para non_continuous"""
        for vals in vals_list:
            if vals.get('name', _('Nueva')) == _('Nueva'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.suspension') or _('Nueva')
            
            # Para suspensiones no continuas, llenar automáticamente date_from y date_to con las fechas de las líneas
            if vals.get('modality') == 'non_continuous':
                lines = vals.get('suspension_line_ids', [])
                dates = []
                
                # Extraer fechas de los comandos de creación
                for line in lines:
                    if line[0] == 0:  # Comando de creación (0, _, {...})
                        suspension_date = line[2].get('suspension_date')
                        if suspension_date:
                            dates.append(suspension_date)
                
                # Si hay fechas, usar la mínima y máxima
                if dates:
                    vals['date_from'] = min(dates)
                    vals['date_to'] = max(dates)
        
        return super(HrSuspension, self).create(vals_list)

    def write(self, vals):
        """Override write para llenar automáticamente fechas en non_continuous"""
        for suspension in self:
            modality = vals.get('modality', suspension.modality)
            
            # Si es non_continuous y se están actualizando las líneas
            if modality == 'non_continuous' and 'suspension_line_ids' in vals:
                lines = vals.get('suspension_line_ids', [])
                # Obtener fechas existentes (que no se están eliminando)
                existing_dates = [
                    line.suspension_date 
                    for line in suspension.suspension_line_ids
                    if not any(l[0] == 2 and l[1] == line.id for l in lines)  # Excluir eliminadas
                ]
                dates = list(existing_dates)
                
                # Agregar fechas nuevas
                for line in lines:
                    if line[0] == 0:  # Crear
                        suspension_date = line[2].get('suspension_date')
                        if suspension_date:
                            dates.append(suspension_date)
                    elif line[0] == 1:  # Actualizar
                        suspension_date = line[2].get('suspension_date')
                        if suspension_date:
                            dates.append(suspension_date)
                
                # Llenar fechas si hay líneas
                if dates:
                    vals['date_from'] = min(dates)
                    vals['date_to'] = max(dates)
        
        return super(HrSuspension, self).write(vals)

    def action_confirm(self):
        """Confirma la suspensión"""
        # Para suspensiones no continuas, auto-llenar date_from y date_to si no están llenados
        for suspension in self:
            if suspension.modality == 'non_continuous' and (not suspension.date_from or not suspension.date_to):
                valid_lines = [line for line in suspension.suspension_line_ids if line.suspension_date]
                if valid_lines:
                    dates = [line.suspension_date for line in valid_lines]
                    suspension.write({
                        'date_from': min(dates),
                        'date_to': max(dates)
                    })
        
        self.write({'state': 'confirm'})

    def action_validate(self):
        """Aprueba la suspensión y crea los registros en hr.leave si no fueron creados desde hr.leave"""
        self.write({'state': 'validate'})
        # Crear los registros en hr.leave SOLO si la suspensión no fue originada desde hr.leave
        for suspension in self:
            # Si leave_id está lleno, significa que fue creada desde hr.leave, así que no crear más registros
            if suspension.leave_id:
                # Solo validar el leave_id existente si no está validado
                if suspension.leave_id.state not in ['validate', 'validate1']:
                    suspension.leave_id.with_context(skip_suspension_creation=True).sudo().action_validate()
            else:
                # Si no tiene leave_id, crear los registros normalmente
                if suspension.modality == 'continuous':
                    suspension._create_leave_record_continuous()
                elif suspension.modality == 'non_continuous':
                    suspension._create_leave_records_non_continuous()

    def action_refuse(self):
        """Rechaza la suspensión"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        """Cancela la suspensión"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Regresa la suspensión a borrador"""
        self.write({'state': 'draft'})

    def _get_suspension_holiday_status(self):
        """Obtiene el tipo de ausencia para suspensiones"""
        holiday_status = self.env['hr.leave.type'].search([
            ('name', '=', 'Suspensión')
        ], limit=1)
        
        if not holiday_status:
            raise ValidationError(
                _('No se encontró el tipo de ausencia "Suspensión". Por favor cree uno en Recursos Humanos > Configuración > Tipo de Ausencia.')
            )
        
        return holiday_status

    def _create_leave_record_continuous(self):
        """Crea un registro de ausencia para suspensión continua"""
        self.ensure_one()
        
        if self.leave_ids:
            return  # Ya existen registros
        
        holiday_status = self._get_suspension_holiday_status()
        
        # Convertir fechas a datetime naive
        date_from = datetime.combine(self.date_from, datetime.min.time())
        date_to = datetime.combine(self.date_to, datetime.max.time())
        
        # Crear el registro de ausencia
        leave_vals = {
            'employee_id': self.employee_id.id,
            'holiday_status_id': holiday_status.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'name': self.reason or ('Suspensión - ' + self.name),
            'supervisor_id': self.supervisor_id.id if self.supervisor_id else False,
            'suspension_id': self.id,
        }
        
        try:
            leave = self.env['hr.leave'].with_context(
                skip_suspension_creation=True,
                leave_skip_state_check=True
            ).sudo().create(leave_vals)
            
            leave.with_context(skip_suspension_creation=True).sudo().action_validate()
        except Exception as e:
            raise ValidationError(
                _('Error al crear la ausencia: %s') % str(e)
            )

    def _create_leave_records_non_continuous(self):
        """Crea múltiples registros de ausencia para suspensión no continua"""
        self.ensure_one()
        
        if self.leave_ids:
            return  # Ya existen registros
        
        holiday_status = self._get_suspension_holiday_status()
        
        for line in self.suspension_line_ids:
            if line.leave_id:
                continue  # Ya existe registro
            
            # Para suspensión de un día
            date_from = datetime.combine(line.suspension_date, datetime.min.time())
            date_to = datetime.combine(line.suspension_date, datetime.max.time())
            
            leave_vals = {
                'employee_id': self.employee_id.id,
                'holiday_status_id': holiday_status.id,
                'date_from': date_from,
                'date_to': date_to,
                'request_date_from': line.suspension_date,
                'request_date_to': line.suspension_date,
                'name': self.reason or ('Suspensión - ' + self.name),
                'supervisor_id': self.supervisor_id.id if self.supervisor_id else False,
                'suspension_id': self.id,
            }
            
            try:
                leave = self.env['hr.leave'].with_context(
                    skip_suspension_creation=True,
                    leave_skip_state_check=True
                ).sudo().create(leave_vals)
                
                leave.with_context(skip_suspension_creation=True).sudo().action_validate()
                
                # Vincular el leave con la línea
                line.leave_id = leave.id
            except Exception as e:
                raise ValidationError(
                    _('Error al crear la ausencia para %s: %s') % (line.suspension_date, str(e))
                )

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permitir búsqueda por número de empleado (biometric_id) en campos Many2one
        """
        if domain is None:
            domain = []
        
        if name:
            # Buscar por folio, biometric_id o nombre del empleado
            domain = ['|', '|', 
                      ('name', operator, name),
                      ('biometric_id', operator, name),
                      ('employee_name', operator, name)]
        
        return self._search(domain, limit=limit, order=order)
