from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from datetime import datetime
from pathlib import Path
import os


class ReportGenerator:
    """Generate PDF reports for inventory system"""

    def __init__(self, config):
        self.config = config
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Setup custom styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12
        ))

    def _create_header(self, canvas, doc):
        """Create page header"""
        canvas.saveState()

        # Company name
        canvas.setFont('Helvetica-Bold', 16)
        canvas.drawString(
            inch, A4[1] - 0.5 * inch, self.config.get('COMPANY_NAME', 'Inventory System'))

        # Page number
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(A4[0] - inch, 0.5 * inch, f"Page {doc.page}")

        canvas.restoreState()

    def generate_inventory_report(self, products, output_path):
        """Generate complete inventory report"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []

        # Title
        title = Paragraph("Inventory Report", self.styles['CustomTitle'])
        story.append(title)

        # Report metadata
        report_date = Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Normal']
        )
        story.append(report_date)
        story.append(Spacer(1, 0.3 * inch))

        # Summary statistics
        total_products = len(products)
        total_quantity = sum(p.quantity for p in products)
        total_value = sum(float(p.cost_price or 0) *
                          (p.quantity or 0) for p in products)
        low_stock_count = sum(1 for p in products if p.is_low_stock)

        summary_data = [
            ['Metric', 'Value'],
            ['Total Products', str(total_products)],
            ['Total Quantity', str(total_quantity)],
            ['Total Value', f"₱{total_value:,.2f}"],
            ['Low Stock Items', str(low_stock_count)]
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 0.5 * inch))

        # Products table
        heading = Paragraph("Product Details", self.styles['CustomHeading'])
        story.append(heading)
        story.append(Spacer(1, 0.2 * inch))

        # Table data
        table_data = [['SKU', 'Product Name',
                       'Category', 'Qty', 'Cost', 'Value']]

        for p in products:
            category_name = p.category.name if p.category else '-'
            value = float(p.cost_price or 0) * (p.quantity or 0)

            table_data.append([
                p.sku,
                p.name[:30] + '...' if len(p.name) > 30 else p.name,
                category_name,
                str(p.quantity or 0),
                f"₱{float(p.cost_price or 0):.2f}",
                f"₱{value:.2f}"
            ])

        products_table = Table(table_data, colWidths=[
                               1 * inch, 2.5 * inch, 1.2 * inch, 0.6 * inch, 0.9 * inch, 1 * inch])
        products_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (5, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.lightgrey])
        ]))

        story.append(products_table)

        # Build PDF
        doc.build(story, onFirstPage=self._create_header,
                  onLaterPages=self._create_header)

        return output_path

    def generate_low_stock_report(self, products, output_path):
        """Generate low stock report"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []

        # Title
        title = Paragraph("Low Stock Alert Report", self.styles['CustomTitle'])
        story.append(title)

        # Report date
        report_date = Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Normal']
        )
        story.append(report_date)
        story.append(Spacer(1, 0.3 * inch))

        # Alert message
        alert = Paragraph(
            "<b>URGENT:</b> The following products are at or below their reorder level.",
            self.styles['Normal']
        )
        story.append(alert)
        story.append(Spacer(1, 0.3 * inch))

        # Products table
        table_data = [['SKU', 'Product Name',
                       'Current Qty', 'Reorder Level', 'Reorder Qty']]

        for p in products:
            table_data.append([
                p.sku,
                p.name[:35] + '...' if len(p.name) > 35 else p.name,
                str(p.quantity or 0),
                str(p.reorder_level),
                str(p.reorder_quantity)
            ])

        products_table = Table(table_data, colWidths=[
                               1.2 * inch, 3 * inch, 1 * inch, 1.2 * inch, 1 * inch])
        products_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.lightgrey])
        ]))

        story.append(products_table)

        # Build PDF
        doc.build(story, onFirstPage=self._create_header,
                  onLaterPages=self._create_header)

        return output_path

    def generate_transaction_report(self, transactions, start_date, end_date, output_path):
        """Generate transaction history report"""
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []

        # Title
        title = Paragraph("Transaction History Report",
                          self.styles['CustomTitle'])
        story.append(title)

        # Date range
        date_range = Paragraph(
            f"<b>Period:</b> {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
            self.styles['Normal']
        )
        story.append(date_range)
        story.append(Spacer(1, 0.3 * inch))

        # Transactions table
        table_data = [['Date', 'Product', 'Type', 'Qty', 'User', 'Reference']]

        for txn in transactions:
            product_name = txn.product.name[:25] + '...' if len(
                txn.product.name) > 25 else txn.product.name
            user_name = txn.user.username if txn.user else 'N/A'

            table_data.append([
                txn.created_at.strftime('%Y-%m-%d %H:%M'),
                product_name,
                txn.transaction_type.upper(),
                str(txn.quantity),
                user_name,
                txn.reference or '-'
            ])

        transactions_table = Table(table_data, colWidths=[
                                   1.3 * inch, 2 * inch, 0.7 * inch, 0.6 * inch, 1 * inch, 1.5 * inch])
        transactions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.lightgrey])
        ]))

        story.append(transactions_table)

        # Build PDF
        doc.build(story, onFirstPage=self._create_header,
                  onLaterPages=self._create_header)

        return output_path
