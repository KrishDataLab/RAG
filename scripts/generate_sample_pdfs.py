from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_hld_v1(filename: str):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1A365D'))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#2B6CB0'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14)

    story = []

    # Page 1: Title, Overview, Component Specification
    story.append(Paragraph("AUTOSAR High-Level Design (HLD) Document", title_style))
    story.append(Paragraph("System: Powertrain Engine Control Unit (ECU)", h2_style))
    story.append(Paragraph("Document Version: v1.0 | Status: Approved", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("1. System Overview", h2_style))
    story.append(Paragraph(
        "The Powertrain Engine Control Unit (ECU) architecture is designed in compliance with AUTOSAR Classic Platform guidelines. "
        "It coordinates real-time sensor data extraction, torque demand processing, throttle positioning, and actuator driving.",
        body_style
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("2. Software Component Specification", h2_style))
    story.append(Paragraph(
        "The system comprises four core Application Software Components (SWCs):\n"
        "1. SpeedSensorComponent (SWC_SpeedSensor): Responsible for reading engine crankshaft pulse inputs and calculating RPM.\n"
        "2. TorqueCalculator (SWC_TorqueCalc): Computes target engine torque based on speed and pedal position.\n"
        "3. ThrottleActuator (SWC_ThrottleActuator): Controls electric throttle body motor via PWM outputs.\n"
        "4. EngineControlUnit (SWC_ECUMain): Coordinates overall ECU state machine and power modes.",
        body_style
    ))
    
    # Page Break to Page 2
    story.append(PageBreak())

    # Page 2: Interface and Port Descriptions
    story.append(Paragraph("3. Interface and Port Descriptions", h2_style))
    story.append(Paragraph(
        "SWC_SpeedSensor provides the SenderReceiver interface RTE_I_EngineSpeed to communicate engine rotation speed to SWC_TorqueCalc. "
        "SWC_SpeedSensor owns PPort_EngineSpeed which carries the signal EngineSpeed_RPM (Range: 0 to 8000 RPM, Resolution: 1 RPM).\n\n"
        "SWC_TorqueCalc requires interface RTE_I_EngineSpeed via RPort_EngineSpeed. SWC_TorqueCalc provides interface RTE_I_ThrottlePosition via PPort_ThrottleCmd to SWC_ThrottleActuator.",
        body_style
    ))
    story.append(Spacer(1, 15))

    data = [
        ["SWC Name", "Port Name", "Port Type", "Interface Name", "Signal Carried"],
        ["SWC_SpeedSensor", "PPort_EngineSpeed", "Provided (PPort)", "RTE_I_EngineSpeed", "EngineSpeed_RPM"],
        ["SWC_TorqueCalc", "RPort_EngineSpeed", "Required (RPort)", "RTE_I_EngineSpeed", "EngineSpeed_RPM"],
        ["SWC_TorqueCalc", "PPort_ThrottleCmd", "Provided (PPort)", "RTE_I_ThrottlePosition", "ThrottleAngle_Deg"],
        ["SWC_ThrottleActuator", "RPort_ThrottleCmd", "Required (RPort)", "RTE_I_ThrottlePosition", "ThrottleAngle_Deg"]
    ]
    t = Table(data, colWidths=[100, 100, 90, 110, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2B6CB0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    
    # Page Break to Page 3
    story.append(PageBreak())

    # Page 3: Functional Flow and Dependencies
    story.append(Paragraph("4. Functional Flow & Dependencies", h2_style))
    story.append(Paragraph(
        "Functional Flow FF_Torque_Control:\n"
        "Step 1: SWC_SpeedSensor samples pulse input and updates EngineSpeed_RPM.\n"
        "Step 2: SWC_TorqueCalc reads EngineSpeed_RPM via RTE_I_EngineSpeed and calculates ThrottleAngle_Deg.\n"
        "Step 3: SWC_ThrottleActuator receives ThrottleAngle_Deg via RTE_I_ThrottlePosition and drives H-Bridge motor.\n\n"
        "Dependency mapping:\n"
        "SWC_TorqueCalc depends_on SWC_SpeedSensor.\n"
        "SWC_ThrottleActuator depends_on SWC_TorqueCalc.",
        body_style
    ))

    doc.build(story)

def create_hld_v2(filename: str):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1A365D'))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=14, leading=18, textColor=colors.HexColor('#2B6CB0'))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14)

    story = []

    # Page 1: Title and Overview
    story.append(Paragraph("AUTOSAR High-Level Design (HLD) Document", title_style))
    story.append(Paragraph("System: Powertrain Engine Control Unit (ECU)", h2_style))
    story.append(Paragraph("Document Version: v1.1 | Status: Under Revision Review", body_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("1. System Overview", h2_style))
    story.append(Paragraph(
        "The Powertrain Engine Control Unit (ECU) architecture version 1.1 introduces an enhanced High-Speed Speed Sensor component (SWC_SpeedSensor_V2) and updates torque request interfaces.",
        body_style
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("2. Software Component Specification", h2_style))
    story.append(Paragraph(
        "The system comprises five Software Components (SWCs):\n"
        "1. SWC_SpeedSensor_V2 (Updated): High-precision speed sensor replacing original SWC_SpeedSensor.\n"
        "2. SWC_TorqueCalc: Computes target engine torque.\n"
        "3. SWC_ThrottleActuator: Controls electric throttle motor.\n"
        "4. SWC_ECUMain: Coordinates ECU power states.\n"
        "5. SWC_SafetyMonitor (NEW Component): Monitors torque safety limits according to ISO 26262 ASIL-D.",
        body_style
    ))
    
    # Page Break to Page 2
    story.append(PageBreak())

    # Page 2: Interfaces and Inconsistencies
    story.append(Paragraph("3. Interface and Port Descriptions", h2_style))
    story.append(Paragraph(
        "SWC_SpeedSensor_V2 provides interface RTE_I_EngineSpeed_HighRes (CHANGED from RTE_I_EngineSpeed).\n"
        "SWC_SpeedSensor_V2 owns PPort_EngineSpeed carrying EngineSpeed_RPM.\n\n"
        "REVISION CHANGE & CONFLICT:\n"
        "SWC_TorqueCalc requires interface RTE_I_EngineSpeed via RPort_EngineSpeed (NOTE: Conflict - SWC_TorqueCalc still expects RTE_I_EngineSpeed while SWC_SpeedSensor_V2 provides RTE_I_EngineSpeed_HighRes).\n"
        "SWC_TorqueCalc provides interface RTE_I_ThrottlePosition_V2 to SWC_ThrottleActuator via PPort_ThrottleCmd.",
        body_style
    ))
    story.append(Spacer(1, 15))

    data = [
        ["SWC Name", "Port Name", "Port Type", "Interface Name", "Signal Carried"],
        ["SWC_SpeedSensor_V2", "PPort_EngineSpeed", "Provided (PPort)", "RTE_I_EngineSpeed_HighRes", "EngineSpeed_RPM"],
        ["SWC_TorqueCalc", "RPort_EngineSpeed", "Required (RPort)", "RTE_I_EngineSpeed", "EngineSpeed_RPM"],
        ["SWC_SafetyMonitor", "RPort_SafetyCheck", "Required (RPort)", "RTE_I_SafetyTorque", "SafetyOverride_Flag"],
        ["SWC_ThrottleActuator", "RPort_ThrottleCmd", "Required (RPort)", "RTE_I_ThrottlePosition_V2", "ThrottleAngle_Deg"]
    ]
    t = Table(data, colWidths=[110, 95, 90, 115, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#C53030')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    
    # Page Break to Page 3
    story.append(PageBreak())

    # Page 3: Functional Flow
    story.append(Paragraph("4. Functional Flow & Dependencies", h2_style))
    story.append(Paragraph(
        "Functional Flow FF_Torque_Control_v2:\n"
        "SWC_SpeedSensor_V2 updates EngineSpeed_RPM -> SWC_SafetyMonitor checks limits -> SWC_TorqueCalc computes torque -> SWC_ThrottleActuator drives throttle.",
        body_style
    ))

    doc.build(story)

if __name__ == "__main__":
    sample_dir = Path(__file__).resolve().parents[1] / "data" / "sample_hld"
    sample_dir.mkdir(parents=True, exist_ok=True)
    create_hld_v1(str(sample_dir / "HLD_v1.0_EngineControl.pdf"))
    create_hld_v2(str(sample_dir / "HLD_v1.1_EngineControl.pdf"))
    print("Sample HLD PDFs generated successfully with explicit page breaks!")
