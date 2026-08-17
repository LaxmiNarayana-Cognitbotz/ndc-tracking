import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

DOC_PATH = r"d:\ndc-tracking\NDC_Email_Automation_and_Template_Guide.docx"

def add_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = tcPr.first_child_found_in("w:tcBorders")
    if tcBorders is None:
        tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
        tcPr.append(tcBorders)
    
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = f'w:{edge}'
            element = parse_xml(f'<{tag} {nsdecls("w")} w:val="{edge_data.get("val", "single")}" w:sz="{edge_data.get("sz", "4")}" w:space="0" w:color="{edge_data.get("color", "CCCCCC")}"/>')
            tcBorders.append(element)

def add_heading_styled(doc, text, level=2):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    if level == 1:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(11, 61, 145) # Navy Blue #0B3D91
    elif level == 2:
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(11, 61, 145)
    elif level == 3:
        run.font.size = Pt(11.5)
        run.font.color.rgb = RGBColor(30, 41, 59)
    return p

def add_metadata_table(doc, data_pairs):
    table = doc.add_table(rows=len(data_pairs) + 1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Header
    h_cells = table.rows[0].cells
    h_cells[0].text = "Configuration & Metadata Attribute"
    h_cells[1].text = "Value / Rule Specification"
    for c in h_cells:
        add_shading(c, "EEF3FB")
        set_cell_margins(c, 100, 100, 150, 150)
        set_cell_border(c, top={"color":"0B3D91","sz":"8"}, bottom={"color":"0B3D91","sz":"8"})
        for p in c.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(11, 61, 145)
    
    for i, (attr, val) in enumerate(data_pairs):
        row_cells = table.rows[i+1].cells
        row_cells[0].text = attr
        row_cells[1].text = val
        for c_idx, c in enumerate(row_cells):
            set_cell_margins(c, 80, 80, 140, 140)
            set_cell_border(c, bottom={"color":"E5E7EB","sz":"4"})
            if c_idx == 0:
                add_shading(c, "F8FAFC")
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    if c_idx == 0:
                        r.bold = True
                        r.font.color.rgb = RGBColor(51, 65, 85)
                    else:
                        r.font.color.rgb = RGBColor(30, 41, 59)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_template_preview_box(doc, header_title, subject_line, greeting, intro_text, sample_headers, sample_rows, warning_box=None, outro_text=None, fnf_kv_rows=None, otp_code=None, action_buttons=None):
    # 1. Subject Line Box
    subj_table = doc.add_table(rows=1, cols=1)
    subj_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = subj_table.rows[0].cells[0]
    add_shading(c, "F1F5F9")
    set_cell_margins(c, 100, 100, 150, 150)
    set_cell_border(c, top={"color":"CBD5E1","sz":"4"}, bottom={"color":"CBD5E1","sz":"4"}, left={"color":"0B3D91","sz":"12"}, right={"color":"CBD5E1","sz":"4"})
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r1 = p.add_run("SUBJECT LINE: ")
    r1.bold = True
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = RGBColor(11, 61, 145)
    r2 = p.add_run(subject_line)
    r2.bold = True
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = RGBColor(15, 23, 42)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    
    # 2. Header Banner Table
    hdr_table = doc.add_table(rows=1, cols=1)
    hdr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hc = hdr_table.rows[0].cells[0]
    add_shading(hc, "0B3D91")
    set_cell_margins(hc, 140, 140, 180, 180)
    hp = hc.paragraphs[0]
    hrun = hp.add_run(header_title)
    hrun.bold = True
    hrun.font.size = Pt(13)
    hrun.font.color.rgb = RGBColor(255, 255, 255)
    
    # 3. Body Table Container
    body_table = doc.add_table(rows=1, cols=1)
    body_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bc = body_table.rows[0].cells[0]
    add_shading(bc, "FFFFFF")
    set_cell_margins(bc, 140, 140, 180, 180)
    set_cell_border(bc, left={"color":"E2E8F0","sz":"4"}, right={"color":"E2E8F0","sz":"4"}, bottom={"color":"E2E8F0","sz":"8"})
    
    # Body text
    bp = bc.paragraphs[0]
    bp.paragraph_format.space_after = Pt(6)
    grun = bp.add_run(greeting + "\n\n")
    grun.font.size = Pt(10)
    grun.font.color.rgb = RGBColor(30, 41, 59)
    
    if warning_box:
        wp = bc.add_paragraph()
        wp.paragraph_format.space_after = Pt(8)
        wrun = wp.add_run(warning_box)
        wrun.bold = True
        wrun.font.size = Pt(9.5)
        wrun.font.color.rgb = RGBColor(217, 83, 79)
    
    ip = bc.add_paragraph()
    ip.paragraph_format.space_after = Pt(8)
    irun = ip.add_run(intro_text)
    irun.font.size = Pt(10)
    irun.font.color.rgb = RGBColor(30, 41, 59)
    
    if otp_code:
        otp_p = bc.add_paragraph()
        otp_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        otp_p.paragraph_format.space_before = Pt(10)
        otp_p.paragraph_format.space_after = Pt(10)
        orun = otp_p.add_run(f"  {otp_code}  ")
        orun.bold = True
        orun.font.size = Pt(22)
        orun.font.color.rgb = RGBColor(11, 61, 145)
    
    # Table inside email
    if fnf_kv_rows:
        kv_table = bc.add_table(rows=len(fnf_kv_rows) + 1, cols=2)
        kv_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        k_cells = kv_table.rows[0].cells
        k_cells[0].text = "Field Name"
        k_cells[1].text = "Field Value Details"
        for kc in k_cells:
            add_shading(kc, "EEF3FB")
            set_cell_margins(kc, 80, 80, 120, 120)
            set_cell_border(kc, bottom={"color":"0B3D91","sz":"6"})
            for kcp in kc.paragraphs:
                for kcr in kcp.runs:
                    kcr.bold = True
                    kcr.font.size = Pt(9)
                    kcr.font.color.rgb = RGBColor(11, 61, 145)
        for r_i, (fk, fv) in enumerate(fnf_kv_rows):
            r_c = kv_table.rows[r_i+1].cells
            r_c[0].text = fk
            r_c[1].text = fv
            for c_i, cc in enumerate(r_c):
                set_cell_margins(cc, 60, 60, 120, 120)
                set_cell_border(cc, bottom={"color":"ECECEC","sz":"4"})
                for ccp in cc.paragraphs:
                    for ccr in ccp.runs:
                        ccr.font.size = Pt(9)
                        if c_i == 0:
                            ccr.bold = True
                            ccr.font.color.rgb = RGBColor(51, 65, 85)
    elif sample_headers and sample_rows:
        grid_table = bc.add_table(rows=len(sample_rows) + 1, cols=len(sample_headers))
        grid_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        g_hcells = grid_table.rows[0].cells
        for col_idx, h_text in enumerate(sample_headers):
            g_hcells[col_idx].text = h_text
            add_shading(g_hcells[col_idx], "EEF3FB")
            set_cell_margins(g_hcells[col_idx], 80, 80, 100, 100)
            set_cell_border(g_hcells[col_idx], bottom={"color":"0B3D91","sz":"6"})
            for ghp in g_hcells[col_idx].paragraphs:
                for ghr in ghp.runs:
                    ghr.bold = True
                    ghr.font.size = Pt(9)
                    ghr.font.color.rgb = RGBColor(11, 61, 145)
        
        for row_i, r_data in enumerate(sample_rows):
            g_rcells = grid_table.rows[row_i+1].cells
            for col_i, c_val in enumerate(r_data):
                g_rcells[col_i].text = c_val
                set_cell_margins(g_rcells[col_i], 60, 60, 100, 100)
                set_cell_border(g_rcells[col_i], bottom={"color":"ECECEC","sz":"4"})
                for grp in g_rcells[col_i].paragraphs:
                    for grr in grp.runs:
                        grr.font.size = Pt(9)
                        grr.font.color.rgb = RGBColor(51, 65, 85)

    if action_buttons:
        ab_p = bc.add_paragraph()
        ab_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ab_p.paragraph_format.space_before = Pt(10)
        ab_p.paragraph_format.space_after = Pt(10)
        b1 = ab_p.add_run(" [ APPROVE ACCESS ] ")
        b1.bold = True
        b1.font.size = Pt(10)
        b1.font.color.rgb = RGBColor(40, 167, 69)
        b2 = ab_p.add_run("   [ REJECT ACCESS ] ")
        b2.bold = True
        b2.font.size = Pt(10)
        b2.font.color.rgb = RGBColor(220, 53, 69)

    if outro_text:
        op = bc.add_paragraph()
        op.paragraph_format.space_before = Pt(8)
        op.paragraph_format.space_after = Pt(4)
        orun = op.add_run(outro_text)
        orun.font.size = Pt(9.5)
        orun.font.color.rgb = RGBColor(30, 41, 59)
    
    so_p = bc.add_paragraph()
    so_p.paragraph_format.space_before = Pt(6)
    so_p.paragraph_format.space_after = Pt(2)
    sorun = so_p.add_run("Regards,\nTeam HR")
    sorun.font.size = Pt(9.5)
    sorun.bold = True
    sorun.font.color.rgb = RGBColor(71, 85, 105)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

def main():
    doc = docx.Document(DOC_PATH)
    
    # Remove any old Section 7 elements to keep document clean and non-duplicated
    for p in doc.paragraphs:
        if p.text.startswith("7. Comprehensive"):
            p_elem = p._element
            body_elems = list(doc._body._element)
            if p_elem in body_elems:
                idx = body_elems.index(p_elem)
                for e in body_elems[idx:]:
                    if not e.tag.endswith("sectPr"):
                        doc._body._element.remove(e)
            break

    add_heading_styled(doc, "7. Comprehensive Department-by-Department Email Templates & Content Guide", level=1)
    
    intro_p = doc.add_paragraph()
    intro_p.paragraph_format.space_after = Pt(8)
    r = intro_p.add_run(
        "This section provides an exhaustive, department-by-department specification of ALL automated and manual email templates in the NDC Tracking System. "
        "Each department workflow includes exact trigger rules, recipient lookup logic, subject line formatting, visual HTML layout mockups, sample content tables, "
        "and dynamic variable mappings."
    )
    r.font.size = Pt(10.5)
    r.font.color.rgb = RGBColor(51, 65, 85)

    standard_headers = ["Employee ID", "Name", "Department", "Last Working Date"]

    # 7.1 Reporting Manager
    add_heading_styled(doc, "7.1 Reporting Manager (RM) Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Reporting Manager Approval (stage_name = 'RM Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Batching & Delay Rules", "Batched in groups of 10 emails; 30-second delay between batches to avoid SMTP throttling"),
        ("Target Recipient Lookup Source", "Mapped via Reporting Manager Name in 'RM Email Configuration Master' (/rm-email-configuration)"),
        ("Conflict Resolution Escalation", "If multiple conflicting emails exist for an RM, email is redirected to HR Central Team with crimson warning box"),
        ("Subject Line Format", "Action Required: Pending RM Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending RM Approval Records",
        subject_line="Action Required: Pending RM Approvals",
        greeting="Dear Rajesh Mehta,",
        intro_text="The following records are currently pending at the RM Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10023451", "Rajesh Kumar", "IT Infrastructure", "15-Aug-2026"],
            ["10028912", "Priya Sharma", "Finance & Accounts", "18-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.2 HR Approval
    add_heading_styled(doc, "7.2 HR Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Human Resources (stage_name = 'HR Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'HR'"),
        ("Subject Line Format", "Action Required: Pending HR Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending HR Approval Records",
        subject_line="Action Required: Pending HR Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the HR Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10034110", "Anil Verma", "Supply Chain", "14-Aug-2026"],
            ["10039821", "Sneha Reddy", "Quality Assurance", "20-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.3 IT Department Approval (Daily & Tomorrow)
    add_heading_styled(doc, "7.3 IT Department Approval Email Templates", level=2)
    add_heading_styled(doc, "7.3.1 Daily 10:00 AM IT Pending Approval Email", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "IT Department (stage_name = 'IT Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'IT'"),
        ("Subject Line Format", "Action Required: Pending IT Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending IT Approval Records",
        subject_line="Action Required: Pending IT Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the IT Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10023451", "Rajesh Kumar", "IT Infrastructure", "15-Aug-2026"],
            ["10041290", "Vikas Gupta", "Software Engineering", "19-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    add_heading_styled(doc, "7.3.2 Daily 10:05 AM IT 'Tomorrow Action Required' Alert", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "IT Department (Tomorrow Alert)"),
        ("Trigger Schedule & Cadence", "Daily @ 10:05 AM IST (Automated Cron Job immediately following main 10 AM run)"),
        ("Trigger Condition Rule", "Scans records where approval stage is 'PENDING' for IT AND employee Last Working Date (LWD) equals Tomorrow (Date.Today + 1)"),
        ("Business Operational Purpose", "Priority alert for hardware asset collection (laptop, monitor, peripherals), email ID deactivation, VPN access revocation"),
        ("Subject Line Format", "Action Required: Pending IT Approvals (Due Tomorrow)")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending IT Approval Records",
        subject_line="Action Required: Pending IT Approvals (Due Tomorrow)",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the IT Approval stage and require your attention:\nNote: The employees listed below have their Last Working Date scheduled for tomorrow (11-Aug-2026).",
        sample_headers=standard_headers,
        sample_rows=[
            ["10023451", "Rajesh Kumar", "IT Infrastructure", "11-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.4 Security Department Approval (Daily & Tomorrow)
    add_heading_styled(doc, "7.4 Security Department Approval Email Templates", level=2)
    add_heading_styled(doc, "7.4.1 Daily 10:00 AM Security Pending Approval Email", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Security Department (stage_name = 'Security Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Security'"),
        ("Subject Line Format", "Action Required: Pending Security Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Security Approval Records",
        subject_line="Action Required: Pending Security Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Security Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10055102", "Manoj Singh", "Plant Operations", "16-Aug-2026"],
            ["10061244", "Kavita Shah", "Logistics", "22-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    add_heading_styled(doc, "7.4.2 Daily 10:05 AM Security 'Tomorrow Action Required' Alert", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Security Department (Tomorrow Alert)"),
        ("Trigger Schedule & Cadence", "Daily @ 10:05 AM IST (Automated Cron Job)"),
        ("Trigger Condition Rule", "Scans records where approval stage is 'PENDING' for Security AND employee LWD equals Tomorrow (Date.Today + 1)"),
        ("Business Operational Purpose", "Priority physical gate pass revocation, biometric access card deactivation, RFID badge recovery"),
        ("Subject Line Format", "Action Required: Pending Security Approvals (Due Tomorrow)")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Security Approval Records",
        subject_line="Action Required: Pending Security Approvals (Due Tomorrow)",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Security Approval stage and require your attention:\nNote: The employees listed below have their Last Working Date scheduled for tomorrow (11-Aug-2026).",
        sample_headers=standard_headers,
        sample_rows=[
            ["10055102", "Manoj Singh", "Plant Operations", "11-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.5 Telecom Approval
    add_heading_styled(doc, "7.5 Telecom Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Telecom Department (stage_name = 'Telecom Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Telecom'"),
        ("Business Scope", "Corporate CUG SIM card deactivation, mobile handset recovery, plan ownership transfer"),
        ("Subject Line Format", "Action Required: Pending Telecom Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Telecom Approval Records",
        subject_line="Action Required: Pending Telecom Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Telecom Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10018823", "Deepak Joshi", "Sales & Marketing", "17-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.6 Administration Approval
    add_heading_styled(doc, "7.6 Administration Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Administration Department (stage_name = 'Administration Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Admin'"),
        ("Business Scope", "Office drawer/locker key surrender, corporate vehicle/parking pass deactivation, ID badge return"),
        ("Subject Line Format", "Action Required: Pending Administration Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Administration Approval Records",
        subject_line="Action Required: Pending Administration Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Administration Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10029981", "Pooja Hegde", "Corporate Admin", "14-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.7 GCC HR Approval
    add_heading_styled(doc, "7.7 GCC HR Department Approval Email Template (Strict Precondition Rule)", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "GCC HR Department (stage_name = 'GCC HR Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("STRICT PRECONDITION RULE", "GCC HR stage is scanned ONLY when ALL 7 prior clearance stages (RM, IT, Telecom, Safety, Admin, Security, HR) are 100% COMPLETED. If any prior stage is pending, employee is omitted."),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'GCC HR'"),
        ("Subject Line Format", "Action Required: Pending GCC HR Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending GCC HR Approval Records",
        subject_line="Action Required: Pending GCC HR Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the GCC HR Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10011928", "Amit Patel", "Finance & Accounts", "12-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.8 Abex Approval
    add_heading_styled(doc, "7.8 Abex Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Abex Department (stage_name = 'ABEX Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Abex'"),
        ("Subject Line Format", "Action Required: Pending ABEX Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending ABEX Approval Records",
        subject_line="Action Required: Pending ABEX Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the ABEX Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10047712", "Rohan Mehra", "ABEX Business Unit", "18-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.9 Store Approval
    add_heading_styled(doc, "7.9 Store Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Store Department (stage_name = 'Store Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Store'"),
        ("Business Scope", "Warehouse tool returns, material inventory clearance, plant store equipment recovery"),
        ("Subject Line Format", "Action Required: Pending Store Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Store Approval Records",
        subject_line="Action Required: Pending Store Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Store Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10058821", "Sanjay Solanki", "Store & Inventory", "15-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.10 Safety Approval
    add_heading_styled(doc, "7.10 Safety Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Safety Department (stage_name = 'Safety Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Safety'"),
        ("Business Scope", "Personal Protective Equipment (PPE) return, safety permit deactivation, plant safety sign-off"),
        ("Subject Line Format", "Action Required: Pending Safety Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Safety Approval Records",
        subject_line="Action Required: Pending Safety Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Safety Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10063319", "Arun Kumar", "EHS & Safety", "17-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.11 Final Abex Approval
    add_heading_styled(doc, "7.11 Final Abex Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Final Abex (stage_name = 'Final ABEX Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Final Abex'"),
        ("Subject Line Format", "Action Required: Pending Final ABEX Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Final ABEX Approval Records",
        subject_line="Action Required: Pending Final ABEX Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Final ABEX Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10047712", "Rohan Mehra", "ABEX Business Unit", "21-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.12 Business Specific Approval
    add_heading_styled(doc, "7.12 Business Specific Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Business Specific (stage_name = 'Business Specific Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Biz Spec'"),
        ("Business Scope", "Specialized BU project handovers, client NDA sign-offs, specialized operational assets"),
        ("Subject Line Format", "Action Required: Pending Business Specific Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Business Specific Approval Records",
        subject_line="Action Required: Pending Business Specific Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Business Specific Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10072210", "Divya Nair", "Strategic Projects", "19-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.13 Legatrix Approval
    add_heading_styled(doc, "7.13 Legatrix Department Approval Email Template", level=2)
    add_metadata_table(doc, [
        ("Department / Stage Name", "Legatrix Approval (stage_name = 'Legatrix Approval')"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST (Automated Cron Job)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'Legatrix'"),
        ("Business Scope", "Statutory compliance clearance, legal non-compete/NDA clearance"),
        ("Subject Line Format", "Action Required: Pending Legatrix Approvals")
    ])
    add_template_preview_box(
        doc,
        header_title="Pending Legatrix Approval Records",
        subject_line="Action Required: Pending Legatrix Approvals",
        greeting="Dear Team,",
        intro_text="The following records are currently pending at the Legatrix Approval stage and require your attention:",
        sample_headers=standard_headers,
        sample_rows=[
            ["10081190", "Tarun Malhotra", "Legal Affairs", "25-Aug-2026"]
        ],
        outro_text="Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
    )

    # 7.14 NDC Delayed Cases Report Email Template
    add_heading_styled(doc, "7.14 NDC Delayed Cases Report Email Template (Top Delayed Records > 30 Days)", level=2)
    add_metadata_table(doc, [
        ("Workflow Name", "NDC Delayed Cases Summary Reminder"),
        ("Trigger Schedule & Cadence", "On-Demand via Dashboard UI / API Endpoint (/send-delayed-reminder)"),
        ("Trigger Condition Rule", "Scans non-completed records (ndc_stage != 'NDC Completed') where pending duration is delayed > 30 days"),
        ("Record Selection Scope", "Includes records delayed by > 30 days, matching the 'Top Delayed Cases' dashboard card, sorted by days delayed descending"),
        ("Target Recipient Lookup Source", "Specified manually in dashboard dialog or configured email recipient master"),
        ("Subject Line Format", "Reminder: Top Delayed NDC Cases ({Date})")
    ])
    add_template_preview_box(
        doc,
        header_title="NDC Delayed Cases Report",
        subject_line="Reminder: Top Delayed NDC Cases (08-Aug-2026)",
        greeting="Hello Team,",
        intro_text="Please find below the top delayed NDC cases identified as of 08-Aug-2026.",
        sample_headers=["Employee ID", "Name", "Department", "Pending Since", "Days Delayed"],
        sample_rows=[
            ["10004120", "Ramesh Verma", "Finance & Accounts", "15-Jul-2026", "24 Days"],
            ["10008819", "Priya Nair", "Operations", "20-Jul-2026", "19 Days"],
            ["10012234", "Sunil Joshi", "IT Infrastructure", "28-Jul-2026", "11 Days"]
        ],
        outro_text="Kindly review and expedite the pending actions to ensure timely closure."
    )

    # 7.15 F&F Team Email Templates
    add_heading_styled(doc, "7.15 F&F Team Email Templates (Open List & Revision Required)", level=2)
    add_heading_styled(doc, "7.14.1 F&F Open List Report Email", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "F&F Team (Open Cases Queue)"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST Cron OR Manual Dashboard UI Dialog ('fnf_open')"),
        ("Trigger Condition Rule", "Scans records where NDC clearance is completed (GCC HR = Completed) but F&F settlement calculations are still OPEN"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'F&F Team'"),
        ("Subject Line Format", "F&F Open List Report - Action Required")
    ])
    add_template_preview_box(
        doc,
        header_title="F&F Open List Records",
        subject_line="F&F Open List Report - Action Required",
        greeting="Hello,",
        intro_text="The following users are currently on the F&F Open list.",
        sample_headers=standard_headers,
        sample_rows=[
            ["10014522", "Suresh Nair", "Operations", "20-Jul-2026"],
            ["10018890", "Alok Sharma", "Commercial", "28-Jul-2026"]
        ],
        outro_text="Please review these records and take the necessary actions."
    )

    add_heading_styled(doc, "7.14.2 F&F Revision Required Alert Email", level=3)
    add_metadata_table(doc, [
        ("Department / Stage Name", "F&F Team (Revision Required Alert)"),
        ("Trigger Schedule & Cadence", "Daily @ 10:00 AM IST Cron OR Manual Dashboard UI Dialog ('fnf_revision')"),
        ("Trigger Condition Rule", "Scans records flagged requiring F&F calculation revision (is_fnf_revision_email_sent set to True upon sending)"),
        ("Target Recipient Lookup Source", "Configured in 'Department Email Recipients Master' (/email-config) under Department = 'F&F Team'"),
        ("Subject Line Format", "F&F Revision Required - Action Required")
    ])
    add_template_preview_box(
        doc,
        header_title="F&F Revision Required Records",
        subject_line="F&F Revision Required - Action Required",
        greeting="Hello,",
        intro_text="The following users currently require F&F Revision.",
        sample_headers=standard_headers,
        sample_rows=[
            ["10021145", "Nitin Desai", "Finance & Accounts", "05-Aug-2026"]
        ],
        outro_text="Please review these records and take the necessary actions."
    )

    # 7.15 Conflicting RM Email Warning
    add_heading_styled(doc, "7.15 Conflicting Manager Email Configuration Warning Email (HR Escalation)", level=2)
    add_metadata_table(doc, [
        ("Workflow Name", "Conflicting RM Manager Email Escalation Alert"),
        ("Trigger Schedule & Cadence", "Evaluated during Daily 10:00 AM Cron execution"),
        ("Trigger Condition Rule", "Triggered when an employee's Reporting Manager name maps to MULTIPLE conflicting email addresses in the RM Email Configuration Master table"),
        ("Target Recipient Lookup Source", "Redirected to HR Central Team ('Department Email Recipients Master' under Department = 'HR')"),
        ("Subject Line Format", "Redirected RM Approvals Report (Conflicting Manager Configurations) - Action Required")
    ])
    add_template_preview_box(
        doc,
        header_title="Conflicting RM Configurations - Redirected Approvals Report",
        subject_line="Redirected RM Approvals Report (Conflicting Manager Configurations) - Action Required",
        greeting="Dear Team,",
        warning_box="Warning: This report has been redirected to HR because there are multiple conflicting email configurations for manager 'Vikram Mehta' in the system.",
        intro_text="The following pending RM approvals have been redirected to HR. Please resolve these duplicate manager entries in the rm_email_configuration database table.",
        sample_headers=["Reporting Manager", "Employee ID", "Name", "Department", "Last Working Date"],
        sample_rows=[
            ["Vikram Mehta", "10034110", "Anil Verma", "Supply Chain", "14-Aug-2026"]
        ],
        outro_text="Please update the RM Email Configuration master table to resolve manager email ambiguity."
    )

    # 7.16 Automated 30-Minute F&F Settlement Direct Employee Mail
    add_heading_styled(doc, "7.16 Automated 30-Minute Full & Final (F&F) Settlement Direct Employee Mail", level=2)
    add_metadata_table(doc, [
        ("Workflow Name", "Automated Direct Employee F&F Settlement Email Delivery"),
        ("Trigger Schedule & Cadence", "Automated Background Cron running every 30 minutes continuously (or manual row click on F&F Data Grid)"),
        ("Trigger Condition Rule", "Scans database for: a) F&F Status Completed (is_fnf_completed = True), b) Email unsent (is_fnf_email_sent = False), c) Settlement document exists on SharePoint/local storage"),
        ("Recipient Lookup Source", "Employee's official email from 'Employee Email Master' (/employee-email-master) via Person Number"),
        ("CC Recipient Rule", "Automatically CCs address configured in FNF_EMAIL_CC / EMAIL_CC environment variable"),
        ("Attachment Processing", "Connects to SharePoint Graph API; attaches PDF (trimmed to max 2 pages) or compresses multiple files into [Person_Number]_documents.zip"),
        ("Subject Line Format", "F&F Settlement Details – {Employee_Name} ({Person_Number})")
    ])
    add_template_preview_box(
        doc,
        header_title="Full & Final Settlement Clearance Details",
        subject_line="F&F Settlement Details – Rajesh Kumar (10023451)",
        greeting="Dear Rajesh Kumar,",
        intro_text="Please find attached your Full & Final Settlement documents for your reference.",
        sample_headers=None,
        sample_rows=None,
        fnf_kv_rows=[
            ("Employee Name:", "Rajesh Kumar"),
            ("Person Number:", "10023451"),
            ("Department:", "IT Infrastructure"),
            ("Resignation Date:", "01-Jul-2026"),
            ("Last Working Date:", "15-Aug-2026"),
            ("F&F Status:", "Completed"),
            ("Completed Date:", "09-Aug-2026"),
            ("Document Count:", "1 Document (Attached PDF)")
        ],
        outro_text="Kindly review the details and inform us if you notice any discrepancy or have any queries.\nWishing you success in your future endeavors."
    )

    # 7.17 Security & Auth Templates
    add_heading_styled(doc, "7.17 System Security & Authentication Automated Email Templates", level=2)
    add_heading_styled(doc, "7.17.1 Two-Factor OTP Login Verification Email", level=3)
    add_metadata_table(doc, [
        ("Workflow Name", "User Authentication OTP Code Dispatch"),
        ("Trigger Cadence", "On-Demand upon user login attempt requiring 2FA"),
        ("Target Recipient", "User's registered email address in NdcUserAccess table"),
        ("Security TTL Rule", "6-digit OTP code expires automatically after 10 minutes"),
        ("Subject Line Format", "NDC Tracking - Login OTP Code")
    ])
    add_template_preview_box(
        doc,
        header_title="NDC Tracking System - Login Verification",
        subject_line="NDC Tracking - Login OTP Code",
        greeting="Dear Rajesh Kumar,",
        intro_text="Your one-time verification code (OTP) for login is:",
        sample_headers=None,
        sample_rows=None,
        otp_code="4 8 2 9 1 0",
        outro_text="This code will expire in 10 minutes. If you did not attempt to log in, please ignore this email."
    )

    add_heading_styled(doc, "7.17.2 First-Time SSO Login Access Request Email (Super Admin Notification)", level=3)
    add_metadata_table(doc, [
        ("Workflow Name", "First-Time SSO Login Access Approval Request"),
        ("Trigger Cadence", "On-Demand when a new user logs in via SSO for the first time without an assigned role"),
        ("Target Recipient", "Super Admin email addresses (role = 'super_admin')"),
        ("Interactive Email Tokens", "Includes single-use HTTP action links for instant web approval or rejection"),
        ("Subject Line Format", "NDC System — New Access Request")
    ])
    add_template_preview_box(
        doc,
        header_title="NDC System — New Access Request",
        subject_line="NDC System — New Access Request",
        greeting="Dear Team,",
        intro_text="A new user has logged in via SSO for the first time and is requesting administrative access to the NDC & F&F Tracking System.\n\nUser Name: Rajesh Kumar\nUser Email: rajesh.kumar@adani.com\nRequested Role: admin",
        sample_headers=None,
        sample_rows=None,
        action_buttons=True,
        outro_text="Please review and act on this request immediately. This email link is single-use and will be invalidated once clicked."
    )

    doc.save(DOC_PATH)
    print("Successfully updated docx file with Section 7!")

if __name__ == "__main__":
    main()
