# -*- coding: utf-8 -*-

from odoo import models, fields, api

class EmployeeDocuments(models.Model):
    _name = 'employee.documents'
    _description = 'Documentos del Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Referencia',
        compute='_compute_name',
        store=True
    )

    # Relación con el empleado
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        tracking=True
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

    # Documentos PDF
    resguardo_baja = fields.Binary(
        string='Resguardo de Baja',
        attachment=True
    )
    resguardo_baja_filename = fields.Char(string='Nombre Resguardo de Baja')

    antidoping = fields.Binary(
        string='Antidoping',
        attachment=True
    )
    antidoping_filename = fields.Char(string='Nombre Antidoping')

    buro_credito = fields.Binary(
        string='Buró de Crédito',
        attachment=True
    )
    buro_credito_filename = fields.Char(string='Nombre Buró de Crédito')

    constancia_situacion_fiscal = fields.Binary(
        string='Constancia de Situación Fiscal',
        attachment=True
    )
    constancia_situacion_fiscal_filename = fields.Char(string='Nombre Constancia Situación Fiscal')

    constancia_nss = fields.Binary(
        string='Constancia de Numero de Seguro Social',
        attachment=True
    )
    constancia_nss_filename = fields.Char(string='Constancia de Numero de Seguro Social')

    carta_antecedentes = fields.Binary(
        string='Carta no Antecedentes Penales',
        attachment=True
    )
    carta_antecedentes_filename = fields.Char(string='Nombre Carta Antecedentes')

    cedula_profesional = fields.Binary(
        string='Cédula Profesional',
        attachment=True
    )
    cedula_profesional_filename = fields.Char(string='Nombre Cédula Profesional')

    contrato_confidencialidad = fields.Binary(
        string='Contrato de Confidencialidad',
        attachment=True
    )
    contrato_confidencialidad_filename = fields.Char(string='Nombre Contrato')

    curp = fields.Binary(
        string='CURP',
        attachment=True
    )
    curp_filename = fields.Char(string='Nombre CURP')

    estudio_socioeconomico = fields.Binary(
        string='Estudio Socio Económico',
        attachment=True
    )
    estudio_socioeconomico_filename = fields.Char(string='Nombre Estudio')

    identificacion_frente = fields.Binary(
        string='Identificación (Frente)',
        attachment=True
    )
    identificacion_frente_filename = fields.Char(string='Nombre ID Frente')

    identificacion_posterior = fields.Binary(
        string='Identificación (Posterior)',
        attachment=True
    )
    identificacion_posterior_filename = fields.Char(string='Nombre ID Posterior')

    titulo = fields.Binary(
        string='Título',
        attachment=True
    )
    titulo_filename = fields.Char(string='Nombre Título')

    certificado_estudios = fields.Binary(
        string='Certificado de Estudios',
        attachment=True
    )
    certificado_estudios_filename = fields.Char(string='Nombre Certificado')

    # Compañía
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='employee_id.company_id',
        store=True,
        readonly=True,
        index=True,
        groups="base.group_multi_company"
    )

    @api.depends('employee_id', 'employee_id.name')
    def _compute_name(self):
        """Generar nombre del registro basado en el empleado"""
        for record in self:
            if record.employee_id:
                record.name = f"Documentos - {record.employee_id.name}"
            else:
                record.name = "Documentos del Empleado"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """
        Permitir búsqueda por número de empleado (biometric_id) en campos Many2one
        """
        if domain is None:
            domain = []
        
        if name:
            # Buscar por biometric_id o nombre del empleado
            domain = ['|', 
                      ('biometric_id', operator, name),
                      ('employee_name', operator, name)]
        
        return self._search(domain, limit=limit, order=order)
