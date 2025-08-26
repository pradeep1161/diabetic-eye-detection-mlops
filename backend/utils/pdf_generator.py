import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

class PDFGenerator:
    def __init__(self, reports_dir):
        self.reports_dir = reports_dir
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
    
    def _create_custom_styles(self):
        custom = {}
        custom['Title'] = ParagraphStyle('CustomTitle', parent=self.styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1d4ed8'), spaceAfter=20, alignment=TA_CENTER)
        custom['Heading'] = ParagraphStyle('CustomHeading', parent=self.styles['Heading2'], fontSize=16, textColor=colors.HexColor('#1d4ed8'), spaceAfter=12, spaceBefore=12)
        custom['SubHeading'] = ParagraphStyle('CustomSubHeading', parent=self.styles['Heading3'], fontSize=14, textColor=colors.HexColor('#374151'), spaceAfter=6)
        custom['Normal'] = ParagraphStyle('CustomNormal', parent=self.styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, spaceAfter=6)
        return custom
    
    def generate_report(self, patient_data, analysis_results, recommendations):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = patient_data.get('name', 'patient').replace(' ', '_')
        filename = f"EyeReport_{safe_name}_{timestamp}.pdf"
        filepath = os.path.join(self.reports_dir, filename)
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        elements = []
        elements.append(Paragraph("AI Vision Care", self.custom_styles['Title']))
        elements.append(Paragraph("Diabetic Eye Disease Analysis Report", self.styles['Heading2']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(f"Report Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("PATIENT INFORMATION", self.custom_styles['Heading']))
        patient_info = [
            ['Name:', patient_data.get('name', 'N/A'), 'Age:', f"{patient_data.get('age', 'N/A')} years"],
            ['Gender:', patient_data.get('gender', 'N/A'), 'Phone:', patient_data.get('phone', 'N/A')],
            ['Diabetes Type:', patient_data.get('diabetesType', 'N/A'), 'Duration:', f"{patient_data.get('diabetesDuration', 'N/A')} years"],
            ['Email:', patient_data.get('email', 'N/A'), 'Report ID:', f"RPT-{timestamp}"]
        ]
        patient_table = Table(patient_info, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        patient_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2ff')), ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#eef2ff')), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c7d2fe'))]))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.3 * inch))
        symptoms = patient_data.get('symptoms', [])
        if symptoms:
            elements.append(Paragraph("REPORTED SYMPTOMS", self.custom_styles['SubHeading']))
            elements.append(Paragraph("".join([f"• {symptom}<br/>" for symptom in symptoms]), self.custom_styles['Normal']))
        elements.append(Paragraph("DIAGNOSTIC ANALYSIS RESULTS", self.custom_styles['Heading']))
        def create_result_table(title, result_data):
            elements.append(Paragraph(title, self.custom_styles['SubHeading']))
            data = [['Detected Condition:', result_data['disease'].replace('_', ' ').title()], ['Confidence Level:', f"{result_data['confidence']}%"], ['Severity Assessment:', result_data['severity']]]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2ff')), ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#c7d2fe'))]))
            elements.append(table); elements.append(Spacer(1, 0.2 * inch))
        if 'fundus' in analysis_results: create_result_table("Fundus Photography Analysis", analysis_results['fundus'])
        if 'oct' in analysis_results: create_result_table("OCT Scan Analysis", analysis_results['oct'])
        elements.append(PageBreak())
        elements.append(Paragraph("AI-GENERATED RECOMMENDATIONS", self.custom_styles['Heading']))
        for line in recommendations.split('\n'):
            line = line.strip()
            if not line: continue
            if line.endswith(':') or line.startswith(('1.', '2.', '3.', '4.', '5.')): elements.append(Paragraph(line, self.custom_styles['SubHeading']))
            elif line.startswith(('-', '•')): elements.append(Paragraph(line, self.custom_styles['Normal'], bulletText='•'))
            else: elements.append(Paragraph(line, self.custom_styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("IMPORTANT NOTICE", self.custom_styles['SubHeading']))
        elements.append(Paragraph("This AI-generated report is for informational purposes only and is not a substitute for professional medical diagnosis. Consult a qualified ophthalmologist for a complete evaluation.", ParagraphStyle('Disclaimer', parent=self.styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))))
        doc.build(elements)
        return os.path.basename(filepath)
