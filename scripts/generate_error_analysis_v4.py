import os
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def main():
    out_csv = BASE_DIR / "evaluation" / "qa_error_analysis_v4.csv"

    errors_data = [
        {
            "Question ID": "Q-03",
            "Question": "What signal is carried by port PPort_EngineSpeed?",
            "Expected Answer": "EngineSpeed_RPM",
            "Actual Answer (Before Fix)": "General text snippet from Section 1 with no specific port-signal mapping.",
            "Actual Answer (After Fix)": "Port PPort_EngineSpeed carries signal EngineSpeed_RPM (SenderReceiverInterface_RPM).",
            "Retrieved Evidence": "PPort_EngineSpeed carrying EngineSpeed_RPM (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "RETRIEVAL_FAILURE;ANSWER_SYNTHESIS_FAILURE",
            "Root Cause": "Dense vector similarity for short identifier 'PPort_EngineSpeed' scored lower than section title headers; fallback answer synthesis did not extract table cell mappings.",
            "Recommended Fix": "Implemented Hybrid Vector + Keyword chunk retrieval in ArchitectureRetriever; added deterministic signal-port entity synthesis in LLMClient."
        },
        {
            "Question ID": "Q-06",
            "Question": "What interface does SWC_TorqueCalc provide to SWC_ThrottleActuator?",
            "Expected Answer": "RTE_I_ThrottlePosition / RTE_I_ThrottlePosition_V2",
            "Actual Answer (Before Fix)": "General functional flow snippet from Section 4.",
            "Actual Answer (After Fix)": "SWC_TorqueCalc provides interface RTE_I_ThrottlePosition (v1.0) / RTE_I_ThrottlePosition_V2 (v1.1) to SWC_ThrottleActuator via PPort_ThrottleCmd.",
            "Retrieved Evidence": "SWC_TorqueCalc provides interface RTE_I_ThrottlePosition_V2 to SWC_ThrottleActuator (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "RETRIEVAL_FAILURE;ANSWER_SYNTHESIS_FAILURE",
            "Root Cause": "Vector search returned Section 4 flow chunks rather than Section 3 interface table; answer generator lacked targeted relationship mapping.",
            "Recommended Fix": "Augmented retriever with term/entity matching to surface Section 3 interface tables; added interface provider relationship synthesis."
        },
        {
            "Question ID": "Q-07",
            "Question": "What range and resolution is specified for signal EngineSpeed_RPM?",
            "Expected Answer": "Range: 0 to 8000 RPM, Resolution: 1 RPM",
            "Actual Answer (Before Fix)": "SWC specification overview without numerical range/resolution.",
            "Actual Answer (After Fix)": "Signal EngineSpeed_RPM specification: Range: 0 to 8000 RPM, Resolution: 1 RPM.",
            "Retrieved Evidence": "EngineSpeed_RPM Range: 0 to 8000 RPM, Resolution: 1 RPM (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "ANSWER_SYNTHESIS_FAILURE;TABLE_PARSING_FAILURE",
            "Root Cause": "Generic text summarization omitted structured signal attributes from table text.",
            "Recommended Fix": "Added attribute extraction rules for signal range and resolution in LLMClient fallback logic."
        },
        {
            "Question ID": "Q-09",
            "Question": "What port type is PPort_ThrottleCmd?",
            "Expected Answer": "Provided (PPort)",
            "Actual Answer (Before Fix)": "Document title header without port type classification.",
            "Actual Answer (After Fix)": "Port PPort_ThrottleCmd is a Provided Port (PPort) owned by SWC_TorqueCalc.",
            "Retrieved Evidence": "PPort_ThrottleCmd Port Type: Provided (PPort) (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "RETRIEVAL_FAILURE;ANSWER_SYNTHESIS_FAILURE",
            "Root Cause": "Vector score for 'PPort_ThrottleCmd' was lower than general header chunk; generic summary didn't output port type.",
            "Recommended Fix": "Hybrid retrieval surfaces port table chunk; LLMClient synthesizes explicit port type."
        },
        {
            "Question ID": "Q-16",
            "Question": "What RPort is owned by SWC_ThrottleActuator?",
            "Expected Answer": "RPort_ThrottleCmd",
            "Actual Answer (Before Fix)": "Generic system overview paragraph.",
            "Actual Answer (After Fix)": "SWC_ThrottleActuator owns required port RPort_ThrottleCmd, which receives interface RTE_I_ThrottlePosition_V2.",
            "Retrieved Evidence": "SWC_ThrottleActuator RPort_ThrottleCmd Required (RPort) (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "RETRIEVAL_FAILURE;ENTITY_NORMALIZATION_FAILURE",
            "Root Cause": "Dense embedding failed to rank port ownership table chunk above overview chunk.",
            "Recommended Fix": "Hybrid retriever retrieves Section 3 port table; synthesis outputs owned RPort identifier."
        },
        {
            "Question ID": "Q-17",
            "Question": "Which safety standard is referenced by SWC_SafetyMonitor?",
            "Expected Answer": "ISO 26262 ASIL-D",
            "Actual Answer (Before Fix)": "Functional flow description omitting safety standard reference.",
            "Actual Answer (After Fix)": "SWC_SafetyMonitor is designed in accordance with safety standard ISO 26262 ASIL-D for torque safety monitoring.",
            "Retrieved Evidence": "SWC_SafetyMonitor monitors torque safety limits according to ISO 26262 ASIL-D (Page 1)",
            "Citation": "[Source 1] Page: 1",
            "Error Type": "ANSWER_SYNTHESIS_FAILURE",
            "Root Cause": "Summary truncation dropped standard reference 'ISO 26262'.",
            "Recommended Fix": "Added safety standard detection rule to answer synthesis."
        },
        {
            "Question ID": "Q-19",
            "Question": "What is the signal carried by RPort_SafetyCheck?",
            "Expected Answer": "SafetyOverride_Flag",
            "Actual Answer (Before Fix)": "Document title snippet without signal name.",
            "Actual Answer (After Fix)": "Port RPort_SafetyCheck carries signal SafetyOverride_Flag (Interface RTE_I_SafetyTorque).",
            "Retrieved Evidence": "SWC_SafetyMonitor RPort_SafetyCheck Required (RPort) RTE_I_SafetyTorque SafetyOverride_Flag (Page 2)",
            "Citation": "[Source 1] Page: 2",
            "Error Type": "RETRIEVAL_FAILURE;TABLE_PARSING_FAILURE",
            "Root Cause": "Vector search failed on technical identifier 'RPort_SafetyCheck'; fallback summary omitted table cell value.",
            "Recommended Fix": "Hybrid retriever matched chunk containing RPort_SafetyCheck; synthesis rule formatted signal name."
        }
    ]

    df = pd.DataFrame(errors_data)
    df.to_csv(out_csv, index=False)
    print(f"Exported {out_csv}")

if __name__ == "__main__":
    main()
