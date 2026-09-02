# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class WarehouseReportController(http.Controller):

    @http.route('/warehouse/report/preview', auth='user', type='http', methods=['GET'])
    def preview_warehouse_report(self, wizard_id=None, **kwargs):
        """Muestra la vista previa del reporte de almacén en HTML"""
        if not wizard_id:
            return request.not_found()
        
        try:
            wizard = request.env['warehouse.report.wizard'].browse(int(wizard_id))
            
            if not wizard.exists():
                return request.not_found()

            html_content = wizard._build_preview_html()
            return request.make_response(
                html_content,
                headers=[('Content-Type', 'text/html; charset=utf-8')]
            )
        except Exception as e:
            _logger.error(f"Error generando reporte: {str(e)}")
            return request.not_found()



